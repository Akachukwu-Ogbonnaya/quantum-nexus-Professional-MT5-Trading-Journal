from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.database import get_universal_connection, conn_fetch_dataframe, universal_execute
from app.utils.logging import add_log
from app.forms.trade_plan import TradePlanForm
import pandas as pd
from datetime import datetime
import json
import time

trade_plan_bp = Blueprint('trade_plan', __name__)

@trade_plan_bp.route('/trade_plan', methods=['GET', 'POST'])
@login_required
def trade_plan():
    """Professional trade planning - HYBRID COMPATIBLE VERSION"""
    form = TradePlanForm()

    if request.method == 'POST':
        try:
            conn = get_universal_connection()
            cursor = conn.cursor()

            # Get data from HTML form fields
            symbol = request.form.get('symbol', '').upper()
            strategy = request.form.get('strategy', '')
            timeframe = request.form.get('timeframe', '')
            plan_date = request.form.get('plan_date', datetime.now().date())
            entry_conditions = request.form.get('entry_conditions', '')
            exit_conditions = request.form.get('exit_conditions', '')
            risk_percent = request.form.get('risk_percent')
            reward_percent = request.form.get('reward_percent')
            status = request.form.get('status', 'pending')
            outcome = request.form.get('outcome', '')

            # Insert into database with PROPER field names
            universal_execute(cursor, '''
                INSERT INTO trade_plans 
                (plan_date, symbol, strategy, timeframe, entry_conditions, exit_conditions, 
                 risk_percent, reward_percent, status, outcome, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                plan_date,
                symbol,
                strategy,
                timeframe,
                entry_conditions,
                exit_conditions,
                risk_percent,
                reward_percent,
                status,
                outcome if outcome else None
            ))

            conn.commit()
            flash('✅ Trade plan saved successfully!', 'success')
            add_log('INFO', f'New trade plan created for {symbol}', 'TradePlan')

            return redirect(url_for('trade_plan.trade_plan'))

        except Exception as e:
            conn.rollback()
            flash(f'❌ Error saving trade plan: {str(e)}', 'danger')
            add_log('ERROR', f'Trade plan save error: {e}', 'TradePlan')
        finally:
            conn.close()

    # Get existing trade plans with PROPER field mapping
    conn = get_universal_connection()
    try:
        # First, let's check if we need to migrate the database schema
        cursor = conn.cursor()

        # Check if new columns exist, if not, create them
        try:
            universal_execute(cursor,
                "SELECT strategy, timeframe, entry_conditions, exit_conditions, risk_percent, reward_percent FROM trade_plans LIMIT 1")
        except Exception:
            # Migrate old schema to new schema
            add_log('INFO', 'Migrating trade_plans schema to new format', 'TradePlan')
            
            # Use universal_execute for all ALTER TABLE statements
            alter_statements = [
                'ALTER TABLE trade_plans ADD COLUMN strategy TEXT',
                'ALTER TABLE trade_plans ADD COLUMN timeframe TEXT',
                'ALTER TABLE trade_plans ADD COLUMN entry_conditions TEXT',
                'ALTER TABLE trade_plans ADD COLUMN exit_conditions TEXT',
                'ALTER TABLE trade_plans ADD COLUMN risk_percent REAL',
                'ALTER TABLE trade_plans ADD COLUMN reward_percent REAL',
                'ALTER TABLE trade_plans ADD COLUMN plan_date DATE'
            ]
            
            for alter_stmt in alter_statements:
                try:
                    universal_execute(cursor, alter_stmt)
                except Exception as alter_error:
                    # Column might already exist, continue
                    add_log('DEBUG', f'Column creation (may already exist): {alter_error}', 'TradePlan')
                    continue

            # Migrate existing data from old fields to new fields
            universal_execute(cursor, '''
                UPDATE trade_plans 
                SET strategy = CASE 
                    WHEN trade_plan LIKE '% - %' THEN substr(trade_plan, 1, instr(trade_plan, ' - ') - 1)
                    ELSE trade_plan 
                END,
                timeframe = CASE 
                    WHEN trade_plan LIKE '% - %' THEN substr(trade_plan, instr(trade_plan, ' - ') + 3)
                    ELSE 'N/A'
                END,
                entry_conditions = CASE 
                    WHEN condition LIKE 'Entry:%' THEN substr(condition, 1, instr(condition, 'Exit:') - 1)
                    ELSE condition
                END,
                exit_conditions = CASE 
                    WHEN condition LIKE '%Exit:%' THEN substr(condition, instr(condition, 'Exit:'))
                    ELSE ''
                END,
                risk_percent = CASE 
                    WHEN notes LIKE 'Risk:%' THEN CAST(replace(substr(notes, instr(notes, 'Risk:') + 5, instr(notes, '%,') - instr(notes, 'Risk:') - 5), '%', '') AS REAL)
                    ELSE NULL
                END,
                reward_percent = CASE 
                    WHEN notes LIKE '%Reward:%' THEN CAST(replace(substr(notes, instr(notes, 'Reward:') + 7, instr(notes, '%', instr(notes, 'Reward:')) - instr(notes, 'Reward:') - 7), '%', '') AS REAL)
                    ELSE NULL
                END,
                plan_date = date
            ''')
            conn.commit()

        # Now query with proper field names
        plans = conn_fetch_dataframe(conn, '''
            SELECT 
                id,
                plan_date,
                symbol,
                strategy,
                timeframe,
                entry_conditions,
                exit_conditions,
                risk_percent,
                reward_percent,
                status,
                outcome,
                created_at
            FROM trade_plans 
            ORDER BY created_at DESC
        ''')

        plans_dict = plans.to_dict('records') if not plans.empty else []

        # Debug output
        print(f"DEBUG: Loaded {len(plans_dict)} trade plans")
        for plan in plans_dict:
            print(f"  Plan {plan.get('id')}: {plan.get('symbol')} - {plan.get('strategy')}")

    except Exception as e:
        add_log('ERROR', f'Error loading trade plans: {e}', 'TradePlan')
        plans_dict = []
        print(f"ERROR loading trade plans: {e}")
    finally:
        conn.close()

    return render_template('trade_plan.html',
                           form=form,
                           trade_plans=plans_dict,
                           current_date=datetime.now().strftime('%Y-%m-%d'))

@trade_plan_bp.route('/edit_trade_plan/<int:plan_id>', methods=['POST'])
@login_required
def edit_trade_plan(plan_id):
    """Edit a trade plan - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()
        cursor = conn.cursor()

        # Get form data
        symbol = request.form.get('symbol', '').upper()
        strategy = request.form.get('strategy', '')
        timeframe = request.form.get('timeframe', '')
        plan_date = request.form.get('plan_date', '')
        entry_conditions = request.form.get('entry_conditions', '')
        exit_conditions = request.form.get('exit_conditions', '')
        risk_percent = request.form.get('risk_percent')
        reward_percent = request.form.get('reward_percent')
        status = request.form.get('status', 'pending')
        outcome = request.form.get('outcome', '')

        # Update the trade plan with PROPER field names
        universal_execute(cursor, '''
            UPDATE trade_plans SET
                plan_date = ?, 
                symbol = ?, 
                strategy = ?, 
                timeframe = ?,
                entry_conditions = ?,
                exit_conditions = ?,
                risk_percent = ?,
                reward_percent = ?,
                status = ?, 
                outcome = ?
            WHERE id = ?
        ''', (
            plan_date,
            symbol,
            strategy,
            timeframe,
            entry_conditions,
            exit_conditions,
            risk_percent,
            reward_percent,
            status,
            outcome if outcome else None,
            plan_id
        ))

        conn.commit()
        flash('✅ Trade plan updated successfully!', 'success')
        add_log('INFO', f'Trade plan {plan_id} updated', 'TradePlan')

    except Exception as e:
        conn.rollback()
        flash(f'❌ Error updating trade plan: {str(e)}', 'danger')
        add_log('ERROR', f'Trade plan update error: {e}', 'TradePlan')
        print(f"ERROR updating trade plan: {e}")
    finally:
        conn.close()

    return redirect(url_for('trade_plan.trade_plan'))

@trade_plan_bp.route('/delete_trade_plan/<int:plan_id>')
@login_required
def delete_trade_plan(plan_id):
    """Delete a trade plan - HYBRID COMPATIBLE VERSION"""
    try:
        conn = get_universal_connection()
        cursor = conn.cursor()

        universal_execute(cursor, 'DELETE FROM trade_plans WHERE id = ?', (plan_id,))
        conn.commit()

        flash('✅ Trade plan deleted successfully!', 'success')
        add_log('INFO', f'Trade plan {plan_id} deleted', 'TradePlan')

    except Exception as e:
        conn.rollback()
        flash(f'❌ Error deleting trade plan: {str(e)}', 'danger')
        add_log('ERROR', f'Trade plan delete error: {e}', 'TradePlan')
    finally:
        conn.close()

    return redirect(url_for('trade_plan.trade_plan'))