from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from decimal import Decimal
from savings_goals_manager import SavingsGoalsManager

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages

# Initialize the SavingsGoalsManager
manager = SavingsGoalsManager()

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/get_family_contributions/<int:user_id>')
def get_family_contributions(user_id):
    try:
        # Get family ID for the user
        family_id = manager.get_family_id(user_id)
        if not family_id:
            return jsonify({'error': 'User not found'}), 404

        # Get all contributions for this family
        query = """
        SELECT s.user_id, s.familygoal_contributed_amount as contribution, 
               s.family_goal, s.family_target_amount, u.name
        FROM savings_goals s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.family_id = %s
        """
        manager.cursor.execute(query, (family_id,))
        results = manager.cursor.fetchall()

        if not results:
            return jsonify({'error': 'No family goal found'}), 404

        # Get the current family goal and target amount
        family_goal = float(results[0]['family_goal']) if results[0]['family_goal'] else 0
        family_target = float(results[0]['family_target_amount']) if results[0]['family_target_amount'] else 0
        total_contributed = sum(float(result['contribution']) for result in results)

        # Prepare response data
        response_data = {
            'users': [{
                'user_id': result['user_id'],
                'contribution': float(result['contribution']),
                'name': result['name'] if 'name' in result else f'User {result["user_id"]}'
            } for result in results],
            'family_goal': family_goal,
            'total_contributed': total_contributed,
            'remaining': family_target,  # Use the actual target amount from database
            'progress': 0 if family_goal == 0 else ((family_goal - family_target) / family_goal * 100)
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error in get_family_contributions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/create_goal', methods=['GET', 'POST'])
def create_goal():
    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            user_goal = float(request.form['user_goal'])
            deadline = request.form['deadline']
            
            # Check if the user is an admin
            is_admin = manager.is_admin(user_id)
            family_goal = request.form.get('family_goal')
            
            if family_goal and not is_admin:
                flash("Only administrators can create family goals.", "error")
                return redirect(url_for('create_goal'))
            
            # Create a family goal if admin
            family_goal = float(family_goal) if family_goal else None
            success = manager.create_savings_goal(user_id, user_goal, deadline, family_goal)
            
            if success:
                flash("Savings goal created successfully!", "success")
            else:
                flash("Failed to create savings goal. Saving goal already exits", "error")
        except ValueError as e:
            flash(f"Invalid input: {str(e)}", "error")
            
        return redirect(url_for('create_goal'))
        
    return render_template('create_goal.html')

@app.route('/check_admin/<int:user_id>')
def check_admin(user_id):
    is_admin = manager.is_admin(user_id)
    return jsonify({'isAdmin': is_admin})

@app.route('/contribute', methods=['GET', 'POST'])
def contribute():
    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            contribution_type = request.form['contribution_type']
            amount = float(request.form['amount'])

            if contribution_type == 'joint':
                joint_id = int(request.form['joint_id'])
                
                # Get current joint goal status
                query = """
                SELECT joint_target_amount
                FROM joint_goals 
                WHERE joint_id = %s
                """
                manager.cursor.execute(query, (joint_id,))
                goal_info = manager.cursor.fetchone()

                if not goal_info:
                    return "ERROR:No joint goal found."

                if goal_info['joint_target_amount'] < amount:
                    return f"ERROR:Contribution exceeds joint target! Maximum allowed: Rs {float(goal_info['joint_target_amount'])}"

                # Update joint goal
                update_query = """
                UPDATE joint_goals 
                SET joint_target_amount = joint_target_amount - %s
                WHERE joint_id = %s
                """
                manager.cursor.execute(update_query, (amount, joint_id))

                # Update user's contribution
                update_participant_query = """
                UPDATE joint_goal_participants 
                SET contributed_amount = contributed_amount + %s
                WHERE joint_id = %s AND user_id = %s
                """
                manager.cursor.execute(update_participant_query, (amount, joint_id, user_id))

                manager.connection.commit()

                # Check if goal is completed
                manager.cursor.execute("""
                    SELECT joint_target_amount 
                    FROM joint_goals 
                    WHERE joint_id = %s
                """, (joint_id,))
                updated_goal = manager.cursor.fetchone()

                if updated_goal['joint_target_amount'] == 0:
                    return "GOAL_COMPLETED:joint:Congratulations! The joint goal has been achieved!"
                
                return f"SUCCESS:Joint goal contribution successful! Remaining: Rs {float(updated_goal['joint_target_amount'])}"

            else:
                # Handle existing user/family contribution logic
                success, message = manager.contribute_to_goal(user_id, contribution_type, amount)
                if success:
                    return f"SUCCESS:{message}"
                return f"ERROR:{message}"

        except ValueError as e:
            return f"ERROR:Invalid input: {str(e)}"

    return render_template('contribute.html')

@app.route('/display_goals', methods=['GET', 'POST'])
def display_goals():
    user_id = None
    goals = []
    family_goals = []
    joint_goals = []
    form_submitted = False
    selected_goal_type = None

    if request.method == 'POST':
        form_submitted = True
        user_id = int(request.form.get('user_id'))
        selected_goal_type = request.form.get('goal_type')
        try:
            if selected_goal_type == "user_goal":
                # Fetch user-specific goals
                manager.cursor.execute("""
                    SELECT 
                        user_id, 
                        user_goal, 
                        user_target_amount, 
                        deadline 
                    FROM savings_goals 
                    WHERE user_id = %s 
                    AND user_goal IS NOT NULL
                """, (user_id,))
                goals = manager.cursor.fetchall()

            elif selected_goal_type == "family_goal":
                # Fetch family goals
                family_id = manager.get_family_id(user_id)
                if family_id:
                    manager.cursor.execute("""
                        SELECT 
                            family_goal, 
                            family_target_amount, 
                            deadline 
                        FROM savings_goals 
                        WHERE family_id = %s 
                        AND family_goal IS NOT NULL
                        LIMIT 1
                    """, (family_id,))
                    family_goals = manager.cursor.fetchall()
                else:
                    flash("Invalid user ID or user does not belong to any family.", "error")

            elif selected_goal_type == "joint_goal":
                # Fetch joint goals
                manager.cursor.execute("""
                    SELECT 
                        jg.joint_id,
                        jg.joint_goal_amount,
                        jg.joint_target_amount,
                        jg.deadline
                    FROM joint_goals jg
                    JOIN joint_goal_participants jgp ON jg.joint_id = jgp.joint_id
                    WHERE jgp.user_id = %s
                """, (user_id,))
                joint_goals = manager.cursor.fetchall()

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")

    return render_template('display_goals.html', 
                           goals=goals, 
                           family_goals=family_goals, 
                           joint_goals=joint_goals, 
                           form_submitted=form_submitted, 
                           selected_goal_type=selected_goal_type,
                           user_id=user_id)

@app.route('/delete_goal/<goal_type>/<int:goal_id>', methods=['POST'])
def delete_goal(goal_type, goal_id):
    r=0
    try:
        if goal_type == 'user':
            manager.delete_user_goal(goal_id)
            flash("User goal deleted successfully!", "success")
            #flash(f"Joint goal with ID {goal_id} deleted successfully.")
        elif goal_type == 'family':
            manager.delete_family_goal(goal_id)
            flash("Family goal deleted successfully!", "success")
        elif goal_type == 'joint':
            user_id = request.form.get('user_id')
            # Validate user_id
            if not user_id:
                flash("User ID is required for joint goals.", "error")
                return redirect(url_for('display_goals'))

            if not user_id.isdigit():
                flash(f"Invalid user ID: {user_id}. Must be a numeric value.", "error")
                return redirect(url_for('display_goals'))
            query="SELECT COUNT(%s) FROM joint_goal_participants WHERE joint_id=%s"
            manager.cursor.execute(query,(goal_id,goal_id,))
            cou=manager.cursor.fetchone()
            print(cou)
            for i in cou.values():
                r=i
                break
            print(r)
            if r<=2:
                num=0
            else:
                num=1
            manager.delete_joint_goal(goal_id, user_id,num)  # Pass user_id to this method
            if num==0:
                flash(f"Joint goal with ID {goal_id} deleted successfully.")
            else:
                flash(f"User {user_id} is withdrawn from the joint goal with ID {goal_id}.")

    except Exception as e:
        flash(f"Failed to delete goal: {str(e)}", "error")
    return redirect(url_for('display_goals'))

@app.route('/create_joint_goal', methods=['GET', 'POST'])
def create_joint_goal():
    if request.method == 'POST':
        # Step 1: Fetch Users by Family ID
        if 'family_id' in request.form and not 'user_ids' in request.form:
            try:
                family_id = int(request.form['family_id'])
                users = manager.get_users_by_family(family_id)

                if not users:
                    flash("No users found for the given family ID.", "error")
                    return render_template('create_joint_goal.html', users=[], family_id=family_id)

                return render_template('create_joint_goal.html', users=users, family_id=family_id)
            except ValueError:
                flash("Invalid family ID. Please enter a valid number.", "error")
                return render_template('create_joint_goal.html', users=[], family_id=None)

        # Step 2: Create Joint Goal
        elif 'user_ids' in request.form:
            try:
                user_ids = request.form.getlist('user_ids')
                joint_goal = float(request.form['joint_goal'])
                deadline = request.form['deadline']

                if len(user_ids) < 2:
                    flash("At least two users are required to create a joint goal.", "error")
                    return redirect(url_for('create_joint_goal'))

                user_ids = [int(user_id) for user_id in user_ids]
                success, message = manager.create_joint_goal(user_ids, joint_goal, deadline)

                if success:
                    flash(message, "success")
                else:
                    flash(message, "error")
            except ValueError:
                flash("Invalid input. Please check the form fields.", "error")
            except Exception as e:
                flash(f"An unexpected error occurred: {str(e)}", "error")

            return redirect(url_for('create_joint_goal'))

    # Initial Form
    return render_template('create_joint_goal.html', users=[], family_id=None)


@app.route('/get_joint_goals/<int:user_id>')
def get_joint_goals(user_id):
    """Get all joint goals for a user"""
    try:
        query = """
        SELECT 
            jg.joint_id,
            jg.joint_goal_amount,
            jg.joint_target_amount,
            jg.deadline
        FROM joint_goals jg
        JOIN joint_goal_participants jgp ON jg.joint_id = jgp.joint_id
        WHERE jgp.user_id = %s AND jg.joint_target_amount > 0
        """
        manager.cursor.execute(query, (user_id,))
        goals = manager.cursor.fetchall()
        
        return jsonify({
            'goals': [{
                'joint_id': goal['joint_id'],
                'joint_goal_amount': float(goal['joint_goal_amount']),
                'joint_target_amount': float(goal['joint_target_amount']),
                'deadline': goal['deadline'].strftime('%Y-%m-%d') if goal['deadline'] else None
            } for goal in goals]
        })
    except Exception as e:
        print(f"Error fetching joint goals: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_user_joint_goals/<int:user_id>')
def get_user_joint_goals(user_id):
    try:
        query = """
        SELECT 
            jg.joint_id,
            jg.joint_goal_amount,
            jg.joint_target_amount,
            jg.deadline
        FROM joint_goals jg
        JOIN joint_goal_participants jgp ON jg.joint_id = jgp.joint_id
        WHERE jgp.user_id = %s
        """
        manager.cursor.execute(query, (user_id,))
        goals = manager.cursor.fetchall()
        return jsonify([{
            'joint_id': goal['joint_id'],
            'joint_goal_amount': float(goal['joint_goal_amount']),
            'joint_target_amount': float(goal['joint_target_amount']),
            'deadline': goal['deadline'].strftime('%Y-%m-%d')
        } for goal in goals])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_joint_contributions/<int:joint_id>')
def get_joint_contributions(joint_id):
    try:
        query = """
        SELECT 
            jg.joint_goal_amount,
            jg.joint_target_amount,
            u.name,
            u.user_id,
            jgp.contributed_amount
        FROM joint_goals jg
        JOIN joint_goal_participants jgp ON jg.joint_id = jgp.joint_id
        JOIN users u ON jgp.user_id = u.user_id
        WHERE jg.joint_id = %s
        """
        manager.cursor.execute(query, (joint_id,))
        results = manager.cursor.fetchall()

        if not results:
            return jsonify({'error': 'Joint goal not found'}), 404

        total_contributed = sum(float(result['contributed_amount']) for result in results)
        joint_goal_amount = float(results[0]['joint_goal_amount'])
        remaining = float(results[0]['joint_target_amount'])

        response_data = {
            'joint_goal_amount': joint_goal_amount,
            'total_contributed': total_contributed,
            'remaining': remaining,
            'progress': 0 if joint_goal_amount == 0 else ((total_contributed / joint_goal_amount) * 100),  # Fixed progress calculation
            'participants': [{
                'user_id': result['user_id'],
                'name': result['name'] if result['name'] else f'User {result["user_id"]}',
                'contribution': float(result['contributed_amount'])
            } for result in results]
        }

        return jsonify(response_data)
    except Exception as e:
        print(f"Error fetching joint contributions: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/delete_joint_goal_action/<int:joint_id>', methods=['POST'])
def delete_joint_goal_action(joint_id):
    """
    Handle the deletion of a joint goal based on user selection:
    - Withdraw contributions.
    - Leave contributions made.
    """
    action = request.form.get('action')
    user_id = int(request.form.get('user_id'))

    try:
        if action == "withdraw":
            manager.delete_joint_goal(joint_id, user_id, 0)  # Withdraw contributions
            flash("Contributions withdrawn and joint goal deleted.", "success")
        elif action == "leave":
            manager.delete_joint_goal(joint_id, user_id, 1)  # Leave contributions
            flash("Left contributions as is and joint goal deleted.", "success")
        else:
            flash("Invalid action for joint goal deletion.", "error")
    except Exception as e:
        flash(f"Error deleting joint goal: {str(e)}", "error")

    return redirect(url_for('display_goals'))


@app.route('/update_goal', methods=['GET', 'POST'])
def update_goal():
    pre_fill_user_id = request.args.get('user_id', '')
    pre_fill_goal_type = request.args.get('goal_type', 'user')

    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            update_type = request.form['update_type']
            new_goal = float(request.form['new_goal'])
            deadline = request.form['deadline']
            confirmation = request.form.get('confirmation', 'no')

            if confirmation != 'yes':
                flash('Update cancelled by user.', 'error')
                return redirect(url_for('update_goal'))

            if update_type == 'joint':
                joint_id = int(request.form['joint_id'])
                
                # Verify user participation
                query = "SELECT 1 FROM joint_goal_participants WHERE joint_id = %s AND user_id = %s"
                manager.cursor.execute(query, (joint_id, user_id))
                if not manager.cursor.fetchone():
                    flash('You are not a participant in this joint goal.', 'error')
                    return redirect(url_for('update_goal'))

                # Update joint goal
                update_query = """
                UPDATE joint_goals 
                SET joint_target_amount = %s,
                    deadline = %s
                WHERE joint_id = %s
                """
                manager.cursor.execute(update_query, (new_goal, deadline, joint_id))
                manager.connection.commit()
                flash('Joint goal updated successfully!', 'success')

            elif update_type == 'user':
                success, message = manager.new_update_goal(user_id, new_goal, deadline)
                flash(message, 'success' if success else 'error')
            else:  # family
                if not manager.is_admin(user_id):
                    flash('Only administrators can update family goals.', 'error')
                    return redirect(url_for('update_goal'))
                success, message = manager.new_update_family_goal(user_id, new_goal, deadline)
                flash(message, 'success' if success else 'error')

        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error updating goal: {str(e)}', 'error')

        return redirect(url_for('update_goal'))

    return render_template('update_goal.html', 
                         pre_fill_user_id=pre_fill_user_id,
                         pre_fill_goal_type=pre_fill_goal_type)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
