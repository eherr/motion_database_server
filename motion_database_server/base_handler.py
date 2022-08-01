
import mimetypes
import tornado.web


mimetypes.add_type("application/html", ".html")
mimetypes.add_type("application/xml", ".xml")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

class BaseHandler(tornado.web.RequestHandler):
    """ https://stackoverflow.com/questions/35254742/tornado-server-enable-cors-requests"""

    def set_default_headers(self):
        self.set_header("access-control-allow-origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'GET, PUT, DELETE, OPTIONS')
        # HEADERS!
        self.set_header("Access-Control-Allow-Headers", "access-control-allow-origin,authorization,content-type")

    def options(self):
        # no body
        self.set_status(204)
        self.finish()

    def get(self):
        error_string = "GET request not implemented. Use POST instead."
        print(error_string)
        self.write(error_string)

class BaseDBHandler(tornado.web.RequestHandler):
    service_name = "MOTION_DB"
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application.get_service_context(self.service_name)
        self.db_path = self.app.db_path
        self.motion_database = self.app.motion_database
