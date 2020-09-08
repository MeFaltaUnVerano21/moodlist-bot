import inspect

from quart import Blueprint

IGNORED_METHODS = [
    '__class__', '__delattr__', '__dir__', '__eq__', '__format__', '__ge__',
    '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__',
    '__le__', '__lt__', '__ne__', '__new__', '__reduce__', '__reduce_ex__',
    '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
    '_find_root_path', 'add_app_template_filter', 'add_app_template_global',
    'add_app_template_test', 'add_url_rule', 'add_websocket', 
    'after_app_request', 'after_app_websocket', 'after_request', 
    'after_websocket', 'app_context_processor', 'app_errorhandler', 
    'app_template_filter', 'app_template_global', 'app_template_test', 
    'app_url_defaults', 'app_url_value_preprocessor', 'before_app_first_request',
    'before_app_request', 'before_app_websocket', 'before_request', 
    'before_websocket', 'context_processor', 'endpoint', 'errorhandler', 
    'get_send_file_max_age', 'make_setup_state', 'open_resource', 'record', 
    'record_once', 'register', 'register_error_handler', 'route', 
    'send_static_file', 'teardown_app_request', 'teardown_request', 
    'teardown_websocket', 'test', 'url_defaults', 'url_value_preprocessor', 
    'websocket'
]

class ClassyBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.routes = {}

    @classmethod
    def _get_method_names(cls):
        methods = [
            func for func in dir(cls)
            if callable(getattr(cls, func))
            and func not in IGNORED_METHODS
            and not str(func).startswith("_")
        ]
        return methods
    
    @classmethod
    def _get_self_name(cls):
        return cls.__name__

    def register(self, app):
        self.app = app
    
        _class_name = self._get_self_name()
        if not self.url_prefix:
            self.url_prefix = f"/{_class_name}"
        
        _methods = self._get_method_names()

        for _method in _methods:
            _obj_class  = repr(self)
            _obj_method = getattr(self, _method)

            kw = inspect.signature(_obj_method)

            if kw.parameters.get("route"):
                route = kw.parameters.get("route")
                
                if route.default == "NO_ROUTE":
                    continue
                
                _route = self.url_prefix + route.default.replace("'", "")
            else:
                if _method == "index":
                    _route = f"{self.url_prefix}"
                else:
                    _route = f"{self.url_prefix}/{_method}/"

            print(f"==> Registering {_route}")

            app.add_url_rule(_route, view_func=_obj_method, methods=["GET", "POST"])
