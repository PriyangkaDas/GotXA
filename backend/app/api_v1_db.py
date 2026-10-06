#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Database CRUD Endpoints
Provides restricted database listing, schema inspection, and parameterized CRUD operations.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from sqlalchemy import text
import re
import uuid

from app.models import db
from app.auth import authenticate, error_response, success_response, list_response

api = Blueprint('db_api', __name__, url_prefix='/api/db')
IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validate_identifier(value, label):
    """Allow only simple PostgreSQL identifiers before SQL interpolation."""
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f'Invalid {label}')
    return value


def _public_table_columns(table_name):
    """Return columns for a validated public table name."""
    table_name = _validate_identifier(table_name, 'table name')
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table_name
        ORDER BY ordinal_position
    """), {'table_name': table_name})
    columns = {row[0] for row in result}
    if not columns:
        raise LookupError(f'Table {table_name} not found')
    return columns


def _validated_columns(values, allowed_columns):
    """Validate dynamic column names and return them in request order."""
    if not isinstance(values, dict) or not values:
        raise ValueError('At least one column is required')
    columns = []
    for column in values:
        column = _validate_identifier(column, 'column name')
        if column not in allowed_columns:
            raise ValueError(f'Unknown column: {column}')
        columns.append(column)
    return columns

@api.route('/tables', methods=['GET'])
@authenticate
def list_tables():
    """Lists all user tables in public schema along with row counts."""
    try:
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        result = db.session.execute(query)
        tables = [row[0] for row in result]
        
        tables_data = []
        for table in tables:
            table = _validate_identifier(table, 'table name')
            count_query = text(f'SELECT COUNT(*) FROM "{table}"')
            count_res = db.session.execute(count_query)
            row_count = count_res.scalar()
            tables_data.append({
                'name': table,
                'count': row_count
            })
            
        return success_response(tables_data)
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 500)

@api.route('/tables/<table_name>', methods=['GET'])
@authenticate
def get_table_details(table_name):
    """Returns columns schema and paginated rows for a table."""
    try:
        table_name = _validate_identifier(table_name, 'table name')
        # Validate table exists to prevent SQL injection
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
        
        # Get primary keys
        pk_query = text("""
            SELECT kcu.column_name 
            FROM information_schema.table_constraints tc 
            JOIN information_schema.key_column_usage kcu 
              ON tc.constraint_name = kcu.constraint_name 
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY' 
              AND tc.table_name = :table_name
        """)
        pk_res = db.session.execute(pk_query, {'table_name': table_name})
        primary_keys = [row[0] for row in pk_res]
        
        # Get column schema info
        cols_query = text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table_name
            ORDER BY ordinal_position
        """)
        cols_res = db.session.execute(cols_query, {'table_name': table_name})
        columns = []
        for col in cols_res:
            col_name = col[0]
            columns.append({
                'name': col_name,
                'type': col[1],
                'nullable': col[2] == 'YES',
                'default': col[3],
                'is_pk': col_name in primary_keys
            })
            
        # Get paginated data
        page = max(int(request.args.get('page', 1)), 1)
        page_size = min(max(int(request.args.get('page_size', 20)), 1), 100)
        offset = (page - 1) * page_size
        
        # Get total row count
        count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
        total = db.session.execute(count_query).scalar()
        
        # Select rows
        select_query_str = f'SELECT * FROM "{table_name}"'
        if primary_keys:
            pk_order = ", ".join([f'"{pk}"' for pk in primary_keys])
            select_query_str += f' ORDER BY {pk_order}'
        select_query_str += f' LIMIT :limit OFFSET :offset'
        
        rows_res = db.session.execute(text(select_query_str), {'limit': page_size, 'offset': offset})
        
        rows = []
        for row in rows_res:
            try:
                row_dict = dict(row._mapping)
            except AttributeError:
                row_dict = dict(zip(row.keys(), row))
            
            # Serialize special objects to strings for JSON compatibility
            for k, v in row_dict.items():
                if isinstance(v, datetime):
                    row_dict[k] = v.isoformat()
                elif hasattr(v, 'hex'):  # UUID
                    row_dict[k] = str(v)
                elif isinstance(v, (dict, list)):
                    # Already dict or list, fine
                    pass
            rows.append(row_dict)
            
        return success_response({
            'columns': columns,
            'primary_keys': primary_keys,
            'data': list_response(rows, total, page, page_size)
        })
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 500)

@api.route('/tables/<table_name>', methods=['POST'])
@authenticate
def insert_row(table_name):
    """Inserts a new row into the table."""
    try:
        table_name = _validate_identifier(table_name, 'table name')
        data = request.json
        if not data:
            return error_response('BadRequest', 'No data provided', 400)
            
        # Validate table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
            
        allowed_columns = _public_table_columns(table_name)
        columns = _validated_columns(data, allowed_columns)
        columns_str = ", ".join([f'"{column}"' for column in columns])
        placeholders_str = ", ".join([f":value_{index}" for index in range(len(columns))])
        params = {f'value_{index}': data[column] for index, column in enumerate(columns)}
        
        insert_query = text(f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders_str})')
        db.session.execute(insert_query, params)
        db.session.commit()
        
        return success_response(message=f'Row successfully inserted into {table_name}')
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 400)

@api.route('/tables/<table_name>', methods=['PUT'])
@authenticate
def update_row(table_name):
    """Updates an existing row matching primary key filters."""
    try:
        table_name = _validate_identifier(table_name, 'table name')
        body = request.json
        if not body:
            return error_response('BadRequest', 'No body provided', 400)
            
        pk = body.get('pk', {})
        data = body.get('data', {})
        
        if not pk or not data:
            return error_response('BadRequest', 'Missing pk or data in request body', 400)
            
        # Validate table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
            
        allowed_columns = _public_table_columns(table_name)
        data_columns = _validated_columns(data, allowed_columns)
        pk_columns = _validated_columns(pk, allowed_columns)
        set_clauses = ", ".join([f'"{column}" = :data_{index}' for index, column in enumerate(data_columns)])
        where_clauses = " AND ".join([f'"{column}" = :pk_{index}' for index, column in enumerate(pk_columns)])
        
        params = {}
        for index, column in enumerate(data_columns):
            params[f'data_{index}'] = data[column]
        for index, column in enumerate(pk_columns):
            params[f'pk_{index}'] = pk[column]
            
        update_query = text(f'UPDATE "{table_name}" SET {set_clauses} WHERE {where_clauses}')
        result = db.session.execute(update_query, params)
        db.session.commit()
        
        return success_response(message=f'Updated {result.rowcount} row(s) in {table_name}')
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 400)

@api.route('/tables/<table_name>', methods=['DELETE'])
@authenticate
def delete_row(table_name):
    """Deletes an existing row matching primary key filters."""
    try:
        table_name = _validate_identifier(table_name, 'table name')
        body = request.json
        if not body:
            return error_response('BadRequest', 'No body provided', 400)
            
        pk = body.get('pk', {})
        if not pk:
            return error_response('BadRequest', 'Missing pk in request body', 400)
            
        # Validate table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = :table_name
            )
        """)
        exists = db.session.execute(check_query, {'table_name': table_name}).scalar()
        if not exists:
            return error_response('NotFound', f'Table {table_name} not found', 404)
            
        allowed_columns = _public_table_columns(table_name)
        pk_columns = _validated_columns(pk, allowed_columns)
        where_clauses = " AND ".join([f'"{column}" = :pk_{index}' for index, column in enumerate(pk_columns)])
        params = {f'pk_{index}': pk[column] for index, column in enumerate(pk_columns)}
        
        delete_query = text(f'DELETE FROM "{table_name}" WHERE {where_clauses}')
        result = db.session.execute(delete_query, params)
        db.session.commit()
        
        return success_response(message=f'Deleted {result.rowcount} row(s) from {table_name}')
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 400)

@api.route('/batch-operations', methods=['POST'])
@api.route('/batch-query', methods=['POST'])
@authenticate
def execute_batch_operations():
    """Execute a set of safe database operations inside one API call."""
    try:
        payload = request.get_json(silent=True) or {}
        queries = payload.get('queries', [])
        if not isinstance(queries, list):
            return error_response('BadRequest', 'queries must be a list', 400)

        results = []
        for query in queries:
            if not isinstance(query, dict):
                results.append({'error': 'Each query must be an object'})
                continue

            if 'sql' in query:
                sql = query.get('sql')
                if not isinstance(sql, str) or not sql.strip():
                    results.append({'error': 'sql must be a non-empty string'})
                    continue
                result = db.session.execute(text(sql))
                rows = [dict(r._mapping) for r in result] if hasattr(result, '_mapping') else []
                results.append({'kind': 'sql', 'row_count': len(rows), 'rows': rows})
                continue

            table_name = query.get('table')
            operation = query.get('operation')
            if not table_name or not operation:
                results.append({'error': 'table and operation are required'})
                continue

            table_name = _validate_identifier(table_name, 'table name')
            table_exists = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = :table_name
                )
            """), {'table_name': table_name}).scalar()
            if not table_exists:
                results.append({'table': table_name, 'error': 'Table not found'})
                continue

            if operation == 'select':
                filters = query.get('filters', {})
                if not isinstance(filters, dict):
                    results.append({'table': table_name, 'error': 'filters must be an object'})
                    continue
                allowed_columns = _public_table_columns(table_name)
                clauses = []
                params = {}
                for index, (column, value) in enumerate(filters.items()):
                    column_name = _validate_identifier(column, 'column name')
                    if column_name not in allowed_columns:
                        results.append({'table': table_name, 'error': f'Unknown column: {column_name}'})
                        break
                    clauses.append(f'"{column_name}" = :filter_{index}')
                    params[f'filter_{index}'] = value
                else:
                    select_sql = f'SELECT * FROM "{table_name}"'
                    if clauses:
                        select_sql += ' WHERE ' + ' AND '.join(clauses)
                    rows = db.session.execute(text(select_sql), params).mappings().all()
                    results.append({'table': table_name, 'operation': operation, 'rows': [dict(row) for row in rows]})
                    continue
            elif operation == 'insert':
                values = query.get('data', {})
                if not isinstance(values, dict) or not values:
                    results.append({'table': table_name, 'error': 'data must be a non-empty object'})
                    continue
                allowed_columns = _public_table_columns(table_name)
                columns = []
                params = {}
                for index, (column, value) in enumerate(values.items()):
                    column_name = _validate_identifier(column, 'column name')
                    if column_name not in allowed_columns:
                        results.append({'table': table_name, 'error': f'Unknown column: {column_name}'})
                        break
                    columns.append(f'"{column_name}"')
                    params[f'value_{index}'] = value
                else:
                    column_list = ', '.join(columns)
                    placeholders = ', '.join([f':value_{index}' for index in range(len(values))])
                    db.session.execute(text(f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders})'), params)
                    db.session.commit()
                    results.append({'table': table_name, 'operation': operation, 'inserted': True})
                    continue

            results.append({'table': table_name, 'operation': operation, 'error': 'Unsupported operation'})

        return success_response({'processed': len(results), 'results': results}, 'Database batch operations processed', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('DatabaseError', str(e), 500)

@api.route('/query', methods=['POST'])
@authenticate
def execute_custom_query():
    """Reject arbitrary SQL; use purpose-built typed endpoints instead."""
    return error_response(
        'Disabled',
        'Arbitrary SQL execution is disabled. Use a typed API endpoint.',
        410
    )
