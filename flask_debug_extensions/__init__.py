from flask import render_template, current_app
from flask_debug import requires_debug


template_folder = 'templates'

def initialize_debug_ext(dbg):
    @dbg.route('/_extensions/')
    @requires_debug
    def debug_list_extensions():
        return render_template('flask_debug/extensions.html', app=current_app)