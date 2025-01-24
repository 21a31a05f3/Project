import mysql.connector
from mysql.connector import Error
import datetime
from decimal import Decimal

class SavingsGoalsManager:
    def __init__(self):
        try:
            # Establish database connection
            self.connection = mysql.connector.connect(
                host='localhost',
                database='projectufft',
                user='root',
                password='Anju@123',
                use_pure=True  # This helps with Decimal handling
            )
            self.cursor = self.connection.cursor(dictionary=True)
        except Error as e:
            print(f"Error connecting to MySQL Platform: {e}")
            raise

    def validate_user(self, user_id):
        """
        Validate if user exists and get user details
        """
        try:
            query = "SELECT * FROM Users WHERE user_id = %s"
            self.cursor.execute(query, (user_id,))
            user = self.cursor.fetchone()
            return user
        except Error as e:
            print(f"Database error during user validation: {e}")
            return None

    def is_admin(self, user_id):
        """
        Check if the user is an admin of the family
        """
        try:
            query = "SELECT role FROM Users WHERE user_id = %s"
            self.cursor.execute(query, (user_id,))
            user = self.cursor.fetchone()
            return user and user['role'].lower() == 'hof'
        except Error as e:
            print(f"Database error checking admin status: {e}")
            return False

    def get_family_id(self, user_id):
        """
        Get the family ID for a given user
        """
        try:
            query = "SELECT family_id FROM Users WHERE user_id = %s"
            self.cursor.execute(query, (user_id,))
            user = self.cursor.fetchone()
            return user['family_id'] if user else None
        except Error as e:
            print(f"Database error getting family ID: {e}")
            return None
        
    def get_joint_id(self, user_id_1):
        """
        Get the joint ID for a given user
        """
        try:
            query = "SELECT joint_id FROM joint_goals WHERE user_id_1= %s"
            self.cursor.execute(query, (user_id_1,))
            joint = self.cursor.fetchone()
            return joint['joint_id'] if joint else None
        except Error as e:
            print(f"Database error getting family ID: {e}")
            return None

    def update_family_goal_for_family(self, family_id, new_family_goal):
        """
        Update the family goal for all users in the same family
        
        Args:
            family_id (int): The ID of the family to update
            new_family_goal (Decimal): The new family goal amount
        
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Convert new_family_goal to Decimal to ensure precision
            new_family_goal = Decimal(str(new_family_goal))

            # Update all savings goals for the family
            update_query = """
            UPDATE savings_goals 
            SET family_goal = %s, 
                family_target_amount = %s 
            WHERE family_id = %s
            """
            
            self.cursor.execute(update_query, (new_family_goal, new_family_goal, family_id))
            self.connection.commit()
            print(f"Family goal set to Rs {new_family_goal} for all family members.")
            return True

        except Error as e:
            print(f"Error updating family goal: {e}")
            self.connection.rollback()
            return False

    def update_savings_goal(self, user_id):
        
        """
        Update savings goal for a user
        
        Args:
            user_id (int): ID of the user updating the goal
        
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Get family ID
            family_id = self.get_family_id(user_id)
            if not family_id:
                print("Could not find family for this user.")
                return False

            # Check if a goal exists for this user
            query = "SELECT * FROM savings_goals WHERE user_id = %s AND family_id = %s"
            self.cursor.execute(query, (user_id, family_id))
            existing_goal = self.cursor.fetchone()
            
            if not existing_goal:
                print("No existing savings goal found for this user.")
                return False

            # Determine update type
            update_type = input("Do you want to update 'user' or 'family' goal? ").lower()

            if update_type == 'user':
                # Regular user can update their own goal
                new_user_goal = float(input("Enter new User Goal Amount: "))
                
                # Confirm user goal update
                confirm = input(f"Confirm updating your goal from Rs {existing_goal['user_goal']} to Rs {new_user_goal}? (yes/no): ").lower()
                if confirm != 'yes':
                    print("Goal update cancelled.")
                    return False

                # Update user goal
                update_query = """
                UPDATE savings_goals 
                SET user_goal = %s, 
                    user_target_amount = %s 
                WHERE user_id = %s AND family_id = %s
                """
                self.cursor.execute(update_query, (
                    Decimal(str(new_user_goal)), 
                    Decimal(str(new_user_goal)), 
                    user_id, 
                    family_id
                ))
                print(f"User goal updated to Rs {new_user_goal} successfully!")

            elif update_type == 'family':
                # Only admin can update family goal
                if not self.is_admin(user_id):
                    print("Only admin can update family goal.")
                    return False

                new_family_goal = float(input("Enter new Family Goal Amount: "))
                
                # Confirm family goal update
                confirm = input(f"Confirm updating family goal from Rs {existing_goal['family_goal']} to Rs {new_family_goal}? (yes/no): ").lower()
                if confirm != 'yes':
                    print("Goal update cancelled.")
                    return False

                # Update family goal for all family members
                self.update_family_goal_for_family(family_id, new_family_goal)
                print(f"Family goal updated to Rs {new_family_goal} successfully!")

            else:
                print("Invalid goal type. Choose 'user' or 'family'.")
                return False

            self.connection.commit()
            return True

        except (Error, ValueError) as e:
            print(f"Error updating savings goal: {e}")
            self.connection.rollback()
            return False
    def new_update_goal(self, user_id, new_user_goal, deadline):
        try:
            family_id = self.get_family_id(user_id)
            if not family_id:
                return False, "Could not find family for this user."

            query = "SELECT * FROM savings_goals WHERE user_id = %s AND family_id = %s"
            self.cursor.execute(query, (user_id, family_id))
            existing_goal = self.cursor.fetchone()
    
            if not existing_goal:
                return False, "No existing savings goal found for this user."

            update_query = """
            UPDATE savings_goals 
            SET user_goal = %s, 
                user_target_amount = %s,
                deadline = %s
            WHERE user_id = %s AND family_id = %s
            """
            self.cursor.execute(update_query, (
                Decimal(str(new_user_goal)), 
                Decimal(str(new_user_goal)), 
                deadline,
                user_id, 
                family_id
            ))
            self.connection.commit()
            return True, f"User goal updated to Rs {new_user_goal} successfully!"

        except (Error, ValueError) as e:
            self.connection.rollback()
            return False, f"Error updating savings goal: {e}"

    def new_update_family_goal(self, user_id, new_family_goal, deadline):
        try:
            family_id = self.get_family_id(user_id)
            if not family_id:
                return False, "Could not find family for this user."

            if not self.is_admin(user_id):
                return False, "Only admin can update family goal."

            # Update family goal including deadline
            update_query = """
            UPDATE savings_goals 
            SET family_goal = %s,
                family_target_amount = %s,
                deadline = %s
            WHERE family_id = %s
            """
            self.cursor.execute(update_query, (
                Decimal(str(new_family_goal)),
                Decimal(str(new_family_goal)),
                deadline,
                family_id
            ))
            self.connection.commit()
            return True, f"Family goal updated to Rs {new_family_goal} successfully!"

        except (Error, ValueError) as e:
            self.connection.rollback()
            return False, f"Error updating family goal: {e}"
    def create_savings_goal(self, user_id, user_goal, deadline, family_goal=None):
        """
        Create a new savings goal for a user
        """
        try:
            # Validate user
            user = self.validate_user(user_id)
            if not user:
                print("Invalid User ID")
                return False
            if user_goal <= 0:
                print("Saving goal cannot be zero or negative!")
                return False
            
            # Get family ID
            family_id = user['family_id']

            # Convert user goal to Decimal
            user_goal = Decimal(str(user_goal))

            # Only admin can set a new family goal
            if family_goal is not None and not self.is_admin(user_id):
                print("Only admin can create family goals")
                return False

            # Check if a goal already exists for this user
            query = "SELECT * FROM savings_goals WHERE user_id = %s AND family_id = %s"
            self.cursor.execute(query, (user_id, family_id))
            existing_goal = self.cursor.fetchone()
        
            if existing_goal:
                print("A savings goal for this user already exists.")
                return False

            # Check for existing family goal in the family
            query = "SELECT family_goal, family_target_amount FROM savings_goals WHERE family_id = %s AND family_goal IS NOT NULL LIMIT 1"
            self.cursor.execute(query, (family_id,))
            existing_family_goal = self.cursor.fetchone()

            # Determine which family goal to use
            final_family_goal = None
            final_family_target = None

            if self.is_admin(user_id) and family_goal is not None:
                # Admin is setting a new family goal
                final_family_goal = Decimal(str(family_goal))
                final_family_target = final_family_goal
            elif existing_family_goal:
                # Use existing family goal for new member
                final_family_goal = existing_family_goal['family_goal']
                final_family_target = existing_family_goal['family_target_amount']

            # Insert new savings goal
            if final_family_goal is not None:
                query = """
                INSERT INTO savings_goals 
                (family_id, user_id, user_goal, family_goal, 
                user_target_amount, family_target_amount, usergoal_contributed_amount,  familygoal_contributed_amount, deadline) 
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0, %s)
                """
                values = (family_id, user_id, user_goal, final_family_goal, 
                        user_goal, final_family_target, deadline)
            
                # If admin is setting a new family goal, update it for all existing members
                if self.is_admin(user_id) and family_goal is not None:
                    self.update_family_goal_for_family(family_id, family_goal)
            else:
                # No family goal exists
                query = """
                INSERT INTO savings_goals 
                (family_id, user_id, user_goal, 
                user_target_amount, usergoal_contributed_amount,  familygoal_contributed_amount, deadline) 
                VALUES (%s, %s, %s, %s, 0, 0, %s)
                """
                values = (family_id, user_id, user_goal,
                        user_goal, deadline)
        
            self.cursor.execute(query, values)
            self.connection.commit()
            print("Savings goal created successfully!")
            return True

        except Error as e:
            print(f"Error creating savings goal: {e}")
            self.connection.rollback()
            return False
    
    def get_users_by_family(self, family_id):
        """
        Fetch all users belonging to a specific family.
        """
        try:
            query = "SELECT user_id, name FROM Users WHERE family_id = %s"
            self.cursor.execute(query, (family_id,))
            return self.cursor.fetchall()
        except Error as e:
            print(f"Database error fetching users by family ID: {e}")
            return []

    def create_joint_goal(self, user_ids, joint_goal_amount, deadline):
        """
        Create a joint savings goal for multiple users.
        """
        try:
            if len(user_ids) < 2:
                return False, "At least two users are required for a joint goal."

            # Validate users and family ID
            family_id = None
            for user_id in user_ids:
                user = self.validate_user(user_id)
                if not user:
                    return False, f"Invalid User ID: {user_id}"
                if family_id is None:
                    family_id = user['family_id']
                elif family_id != user['family_id']:
                    return False, "All users must belong to the same family."

            # Check if goal amount is valid
            joint_goal_amount = Decimal(str(joint_goal_amount))
            if joint_goal_amount <= 0:
                return False, "Joint goal amount must be greater than zero."

            # Create the joint goal
            insert_joint_goal_query = """
            INSERT INTO joint_goals (joint_goal_amount, joint_target_amount, deadline) 
            VALUES (%s, %s, %s)
            """
            self.cursor.execute(insert_joint_goal_query, (
                joint_goal_amount,
                joint_goal_amount,
                deadline
            ))
            joint_id = self.cursor.lastrowid

            # Add participants
            for user_id in user_ids:
                insert_participant_query = """
                INSERT INTO joint_goal_participants (joint_id, user_id, contributed_amount)
                VALUES (%s, %s, 0)
                """
                self.cursor.execute(insert_participant_query, (joint_id, user_id))

            self.connection.commit()
            return True, f"Joint goal of Rs {joint_goal_amount} created successfully for {len(user_ids)} users!"
        except Error as e:
            self.connection.rollback()
            return False, f"Error creating joint goal: {str(e)}"

    def contribute_to_goal(self, user_id, contribution_type, amount):
        """
        Contribute to either user or family goal with detailed error handling.
        """
        try:
            # Get family ID for the user
            family_id = self.get_family_id(user_id)
            if not family_id:
                return False, "Could not find family for this user."

            # Convert the contribution amount to Decimal to ensure precision
            amount = Decimal(str(amount))
            if amount <= 0:
                return False, "Contribution amount must be greater than zero."

            # Fetch current savings goal for the user
            query = "SELECT * FROM savings_goals WHERE family_id = %s AND user_id = %s"
            self.cursor.execute(query, (family_id, user_id))
            goal = self.cursor.fetchone()

            if not goal:
                return False, "No savings goal found for this user in the family."

            # Handle user contribution
            if contribution_type == 'user':
                new_user_target = goal['user_target_amount'] - amount
                if new_user_target < 0:
                    remaining = goal['user_target_amount']
                    return False, f"Contribution exceeds remaining target! Maximum allowed contribution is Rs{remaining}"

                # Update the user's savings goal
                update_query = """
                UPDATE savings_goals 
                SET user_target_amount = %s, 
                    usergoal_contributed_amount = usergoal_contributed_amount + %s 
                WHERE family_id = %s AND user_id = %s
                """
                self.cursor.execute(update_query, (new_user_target, amount, family_id, user_id))

            # Handle family contribution
            elif contribution_type == 'family':
                if goal['family_target_amount'] is None:
                    return False, "A family goal has not yet been created by your admin!"
                
                new_family_target = goal['family_target_amount'] - amount
                if new_family_target < 0:
                    remaining = goal['family_target_amount']
                    return False, f"Contribution exceeds family target! Maximum allowed contribution is Rs{remaining}"

                # Update the family target for all users in the same family
                update_query_family_target = """
                UPDATE savings_goals 
                SET family_target_amount = %s
                WHERE family_id = %s
                """
                self.cursor.execute(update_query_family_target, (new_family_target, family_id))

                # Update the contributing user's current amount towards the family goal
                update_query_user_contribution = """
                UPDATE savings_goals 
                SET familygoal_contributed_amount = familygoal_contributed_amount + %s
                WHERE family_id = %s AND user_id = %s
                """
                self.cursor.execute(update_query_user_contribution, (amount, family_id, user_id))

            else:
                return False, "Invalid contribution type. Choose 'user' or 'family'."

            # Commit the transaction to save changes
            self.connection.commit()
            return True, "Contribution successful!"

        except (Error, ValueError) as e:
            self.connection.rollback()
            return False, f"Error processing contribution: {str(e)}"

    def contribute_to_joint_goal(self, user_id, amount):
        """
        Contribute to a joint goal
        """
        try:
            # Get all joint goals the user is part of
            query = """
            SELECT jg.joint_id, jg.joint_goal_amount, jg.joint_target_amount, jg.deadline,
                jgp.contributed_amount
            FROM joint_goals jg
            JOIN joint_goal_participants jgp ON jg.joint_id = jgp.joint_id
            WHERE jgp.user_id = %s AND jg.joint_target_amount > 0
            """
            self.cursor.execute(query, (user_id,))
            joint_goals = self.cursor.fetchall()
            
            if not joint_goals:
                return False, "No active joint goals found for this user."

            # If multiple joint goals exist, let user choose
            if len(joint_goals) > 1:
                print("\nAvailable Joint Goals:")
                for idx, goal in enumerate(joint_goals, 1):
                    print(f"{idx}. Goal Amount: Rs{goal['joint_goal_amount']}, " 
                        f"Remaining: Rs{goal['joint_target_amount']}, "
                        f"Your Contribution: Rs{goal['contributed_amount']}, "
                        f"Deadline: {goal['deadline']}")
                
                while True:
                    try:
                        choice = int(input("\nSelect joint goal number: ")) - 1
                        if 0 <= choice < len(joint_goals):
                            selected_goal = joint_goals[choice]
                            break
                        print("Invalid selection. Please try again.")
                    except ValueError:
                        print("Please enter a valid number.")
            else:
                selected_goal = joint_goals[0]

            amount = Decimal(str(amount))
            if amount <= 0:
                return False, "Contribution amount must be greater than zero."

            # Check if contribution exceeds remaining target
            if selected_goal['joint_target_amount'] < amount:
                return False, f"Contribution exceeds remaining target! Maximum allowed: Rs{selected_goal['joint_target_amount']}"

            # Update joint goal target and contribution
            update_joint_goal_query = """
            UPDATE joint_goals 
            SET joint_target_amount = joint_target_amount - %s
            WHERE joint_id = %s
            """
            update_participant_query = """
            UPDATE joint_goal_participants 
            SET contributed_amount = contributed_amount + %s
            WHERE joint_id = %s AND user_id = %s
            """
            
            self.cursor.execute(update_joint_goal_query, (amount, selected_goal['joint_id']))
            self.cursor.execute(update_participant_query, (amount, selected_goal['joint_id'], user_id))
            
            self.connection.commit()
            return True, f"Successfully contributed Rs {amount} to joint goal!"

        except Error as e:
            self.connection.rollback()
            return False, f"Error contributing to joint goal: {str(e)}"
    def display_savings_goal(self):
        """
        Display current savings goal details
        """
        try:
            user_id = int(input("Enter User ID: "))
            
            # Get family ID
            family_id = self.get_family_id(user_id)
            if not family_id:
                print("Could not find family for this user.")
                return

            # Fetch all goals for the family
            query = "SELECT * FROM savings_goals WHERE family_id = %s"
            self.cursor.execute(query, (family_id,))
            goals = self.cursor.fetchall()

            if goals:
                print("\n--- Family Savings Goals ---")
                for goal in goals:
                    print(f"\nUser ID: {goal['user_id']}")
                    print(f"User Goal: Rs{goal['user_goal']}")
                    print(f"User Target Remaining: Rs {goal['user_target_amount']}")
                    
                    # Only display family goal once
                    if goal == goals[0]:
                        print(f"Family Goal: Rs {goal['family_goal']}")
                        print(f"Family Target Remaining: Rs {goal['family_target_amount']}")
                        print(f"User Goal Contributed Amount: Rs {goal['usergoal_contributed_amount']}")
                        print(f"Family Goal Contributed Amount: Rs {goal['familygoal_contributed_amount']}")
                        print(f"Total Contributed Amount: Rs {goal['familygoal_contributed_amount']+goal['usergoal_contributed_amount']}")
                        print(f"Deadline: {goal['deadline']}")
            else:
                print("No savings goals found for this family.")

        except Error as e:
            print(f"Error displaying savings goal: {e}")
    def display_joint_goals(self, user_id):
        """
        Display all joint goals for a user
        """
        try:
            query = """
            SELECT 
                jg.joint_id,
                jg.joint_goal_amount,
                jg.joint_target_amount,
                jg.deadline,
                jgp.contributed_amount as user_contribution,
                GROUP_CONCAT(u.username) as participants,
                GROUP_CONCAT(jgp2.contributed_amount) as all_contributions
            FROM joint_goals jg
            JOIN joint_goal_participants jgp ON jg.joint_id = jgp.joint_id
            JOIN joint_goal_participants jgp2 ON jg.joint_id = jgp2.joint_id
            JOIN users u ON jgp2.user_id = u.user_id
            WHERE jgp.user_id = %s
            GROUP BY jg.joint_id, jgp.contributed_amount
            """
            self.cursor.execute(query, (user_id,))
            goals = self.cursor.fetchall()

            if not goals:
                print("No joint goals found for this user.")
                return

            print("\n=== Your Joint Goals ===")
            for goal in goals:
                print(f"\nJoint Goal ID: {goal['joint_id']}")
                print(f"Total Goal Amount: Rs {goal['joint_goal_amount']}")
                print(f"Remaining Target: Rs {goal['joint_target_amount']}")
                print(f"Your Contribution: Rs {goal['user_contribution']}")
                print(f"Deadline: {goal['deadline']}")
                
                # Display all participants and their contributions
                participants = goal['participants'].split(',')
                contributions = goal['all_contributions'].split(',')
                print("\nParticipants:")
                for participant, contribution in zip(participants, contributions):
                    print(f"- {participant}: Rs {contribution}")

        except Error as e:
            print(f"Error displaying joint goals: {str(e)}")
    
    def delete_user_goal(self, user_id):
        try:
            # query = "DELETE FROM savings_goals WHERE user_id = %s"
            query="UPDATE savings_goals SET user_goal=%s, user_target_amount=%s, usergoal_contributed_amount=%s WHERE user_id=%s"
            self.cursor.execute(query, (None,None,None,user_id,))
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            raise Exception(f"Error deleting user goal: {e}")

    def delete_family_goal(self, family_id):
        """
        Delete all savings goals for a family.
        """
        try:
            # query = "DELETE FROM savings_goals WHERE family_id = %s"
            query="UPDATE savings_goals SET family_goal=%s, family_target_amount=%s, familygoal_contributed_amount=%s WHERE family_id=%s"
            self.cursor.execute(query, (None,None,None,family_id,))
            self.connection.commit()
        except Error as e:
            self.connection.rollback()
            raise Exception(f"Error deleting family goal: {e}")

    def delete_joint_goal(self, joint_id, user_id, leave_contributions):
        """
        Delete or adjust a joint goal based on user action.
        Args:
            joint_id: ID of the joint goal.
            user_id: ID of the user performing the action.
            leave_contributions: Flag to leave contributions (1) or withdraw (0).
        """
        try:
            if leave_contributions == 1:
                # Remove the user from the joint goal but keep contributions
                delete_query = "DELETE FROM joint_goal_participants WHERE joint_id = %s AND user_id = %s"
                self.cursor.execute(delete_query, (joint_id, user_id))
            else:
                # Refund contributions and remove the user
                refund_query = """
                    UPDATE joint_goals 
                    SET joint_target_amount = joint_target_amount + 
                        (SELECT contributed_amount 
                        FROM joint_goal_participants 
                        WHERE joint_id = %s AND user_id = %s)
                    WHERE joint_id = %s
                """
                self.cursor.execute(refund_query, (joint_id, user_id, joint_id))
                delete_query = "DELETE FROM joint_goal_participants WHERE joint_id = %s AND user_id = %s"
                self.cursor.execute(delete_query, (joint_id, user_id))

            # If no participants remain, delete the joint goal
            self.cursor.execute("SELECT COUNT(*) AS count FROM joint_goal_participants WHERE joint_id = %s", (joint_id,))
            result = self.cursor.fetchone()
            if result and result['count'] == 0:
                self.cursor.execute("DELETE FROM joint_goals WHERE joint_id = %s", (joint_id,))

            self.connection.commit()
        except Error as e:
            self.connection.rollback()
            raise Exception(f"Error managing joint goal deletion: {e}")



    def track(self, user_id):
        """
        Track progress of user and family goals. 
        Prompts for new goals when target amounts are reached.
        """
        # Get family ID
        family_id = self.get_family_id(user_id)
        if not family_id:
            print("Could not find family for this user.")
            return

        # Check if the user's individual target is 0
        query = "SELECT user_id FROM savings_goals WHERE user_target_amount = 0"
        self.cursor.execute(query)
        res = self.cursor.fetchall()

        for i in res:
            if i['user_id'] == user_id:
                print("You have reached your saving goal! Please create a new goal.")
                try:
                    new_user_goal = float(input("Enter new User Goal Amount: "))
                    if new_user_goal <= 0:
                        raise ValueError("User goal must be greater than 0.")
                    deadline = input("Enter new deadline (YYYY-MM-DD): ")
                    datetime.datetime.strptime(deadline, "%Y-%m-%d")  # Validate date format
                    self.new_update_goal(user_id, new_user_goal, deadline)
                except ValueError as e:
                    print(f"Invalid input: {e}")
                    return

        # Check if the family's target is 0
        query1 = "SELECT family_id FROM savings_goals WHERE family_target_amount = 0"
        self.cursor.execute(query1)
        res1 = self.cursor.fetchall()
        for i in res1:
            if i['family_id'] == family_id:
                print("You have completed your family saving goal!")
                try:
                    new_family_goal = float(input("Enter new Family Goal Amount: "))
                    if new_family_goal <= 0:
                        raise ValueError("Family goal must be greater than 0.")
                    deadline = input("Enter new deadline (YYYY-MM-DD): ")
                    datetime.datetime.strptime(deadline, "%Y-%m-%d")  # Validate date format
                    success, message = self.new_update_family_goal(user_id, new_family_goal, deadline)
                    if success:
                        print("A new family goal has been set!")
                    else:
                        print(f"Failed to set a new family goal: {message}")
                except ValueError as e:
                    print(f"Invalid input: {e}")
                break

    def is_goal_zero(self, user_id, contribution_type):
        try:
            if contribution_type == "user":
                self.cursor.execute("SELECT user_goal FROM savings_goals WHERE user_id = %s", (user_id,))
            elif contribution_type == "family":
                self.cursor.execute("SELECT family_goal FROM savings_goals WHERE family_id = (SELECT family_id FROM users WHERE user_id = %s)", (user_id,))
            else:
                return True

            result = self.cursor.fetchone()
            return result and result[0] == 0
        except Exception as e:
            print(f"Error checking goal: {e}")
            return True
    def get_user_goal_info(self, user_id):
        """Get user's goal and current savings information"""
        try:
            query = """
            SELECT user_goal, user_target_amount, usergoal_contributed_amount,familygoal_contributed_amount 
            FROM savings_goals 
            WHERE user_id = %s
            """
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'total_goal': result['user_goal'],
                    'remaining': result['user_target_amount'],
                    'usergoal_contributed_amount': result['usergoal_contributed_amount'],
                    'familygoal_contributed_amount': result['familygoal_contributed_amount']

                }
            return None
        except Error as e:
            print(f"Error getting user goal info: {e}")
            return None

def main():
    manager = SavingsGoalsManager()
    while True:
        print("\n--- Unified Family Finance Tracker ---")
        print("1. Create User Savings Goal")
        print("2. Create Joint Savings Goal")
        print("3. Contribute to Savings Goal")
        print("4. Contribute to Joint Goal")
        print("5. Display Family Savings Goals")
        print("6. Display Joint Goals")
        print("7. Update Savings Goal")
        print("8. Exit")

        choice = input("Enter your choice (1-8): ")

        try:
            if choice == '1':
                user_id = int(input("Enter User ID: "))
                if manager.is_admin(user_id):
                    user_goal = float(input("Enter User Goal Amount: "))
                    family_goal = float(input("Enter Family Goal Amount (optional, press enter to skip): ") or 0)
                    deadline = input("Enter Deadline (YYYY-MM-DD): ")
                    family_goal = family_goal if family_goal > 0 else None
                    manager.create_savings_goal(user_id, user_goal, deadline, family_goal)
                else:
                    user_goal = float(input("Enter User Goal Amount: "))
                    deadline = input("Enter Deadline (YYYY-MM-DD): ")
                    manager.create_savings_goal(user_id, user_goal, deadline)

            elif choice == '2':
                user_ids = []
                print("Enter User IDs (press Enter when done)")
                while True:
                    user_id = input("Enter User ID (or press Enter to finish adding users): ")
                    if not user_id:
                        break
                    user_ids.append(int(user_id))
                
                if len(user_ids) < 2:
                    print("At least two users are required for a joint goal.")
                    continue
                
                joint_goal = float(input("Enter Joint Goal Amount: "))
                deadline = input("Enter Deadline (YYYY-MM-DD): ")
                success, message = manager.create_joint_goal(user_ids, joint_goal, deadline)
                print(message)

            elif choice == '3':
                user_id = int(input("Enter User ID: "))
                contribution_type = input("Contribute to 'user' or 'family' goal: ").lower()
                amount = float(input("Enter contribution amount: "))
                success, message = manager.contribute_to_goal(user_id, contribution_type, amount)
                print(message)
                manager.track(user_id)

            elif choice == '4':
                user_id = int(input("Enter User ID: "))
                amount = float(input("Enter contribution amount: "))
                success, message = manager.contribute_to_joint_goal(user_id, amount)
                print(message)

            elif choice == '5':
                manager.display_savings_goal()

            elif choice == '6':
                user_id = int(input("Enter User ID: "))
                manager.display_joint_goals(user_id)

            elif choice == '7':
                user_id = int(input("Enter User ID: "))
                manager.update_savings_goal(user_id)

            elif choice == '8':
                print("Exiting the application.")
                break

            else:
                print("Invalid choice. Please try again.")

        except ValueError as e:
            print(f"Invalid input: {str(e)}")

if __name__ == "__main__":
    main()
