from collections import OrderedDict
from functools import wraps
import sys

from flask import current_app, render_template, Blueprint, abort, url_for, redirect, \
    g
import inflection
from jinja2 import PackageLoader, ChoiceLoader


class DebugBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super(DebugBlueprint, self).__init__(*args, **kwargs)
        self.__menu = OrderedDict()
        self.__plugins = None

    def _debug_load_plugins(self):
        if self.__plugins is not None:
            # already loaded
            return

        dbg.__plugins = {}

        for name, mod in sys.modules.items():
            if (name.startswith('flask_debug_') and
                    hasattr(mod, 'initialize_debug_ext')):
                mod.initialize_debug_ext(dbg)
                dbg.__plugins[name] = mod

        # collect loaders
        loaders = [dbg.jinja_loader]
        for name, mod in dbg.__plugins.items():
            template_folder = getattr(mod, 'template_folder', None)
            if template_folder:
                loaders.append(PackageLoader(name, template_folder))

        # replace blueprints loader with new loader that includes extensions
        dbg.jinja_loader = ChoiceLoader(loaders)

    def _debug_get_menu(self):
        return self.__menu

    def route(self, rule, menu_name=True, **options):
        # if only there was nonlocal in py2...
        wrapper = super(DebugBlueprint, self).route(rule, **options)

        @wraps(wrapper)
        def _(f):
            endpoint = options.get('endpoint', f.__name__)

            # menu entry, auto-generated
            name = menu_name
            if name is True:
                name = endpoint
                if name.startswith('debug_'):
                    name = name[len('debug_'):]
                    name = inflection.titleize(name)

            wrapped = wrapper(f)
            if name:
                self.__menu[name] = '{}.{}'.format(self.name, endpoint)
            return wrapped

        return _


dbg = DebugBlueprint('debug', __name__, template_folder='templates')


def requires_debug(view):
    @wraps(view)
    def _(*args, **kwargs):
        if not current_app.debug:
            abort(403, 'This function is only available if the application '
                       'has been started in debug mode.')
        return view(*args, **kwargs)
    return _


@dbg.route('/_debug/', menu_name=None)  # the root
@requires_debug
def debug_root():
    return redirect(url_for('.debug_reflect'))


@dbg.route('/_reflect/')
@requires_debug
def debug_reflect():
    return render_template(
        'flask_debug/reflect.html',
        app=current_app,
    )


@dbg.route('/_config/')
@requires_debug
def debug_config():
    return render_template(
        'flask_debug/config.html',
        app=current_app,
    )


@dbg.before_request
def make_current_app_available():
    g.app = current_app
    g.menu = dbg._debug_get_menu()


class Debug(object):
    def __init__(self, app=None):
        import flask_debug_extensions
        dbg._debug_load_plugins()
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.register_blueprint(dbg)
