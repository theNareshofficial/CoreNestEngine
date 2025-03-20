
from flask import url_for, session, redirect, flash

class SESSION:
    
            def login():
                        if 'user' not in session:
                                    flash("You need to LOGIN!", "error")
                                    return redirect(url_for('login'))
            
            def logout():
                    return session.pop('user', None)
