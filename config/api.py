from django.contrib.admin.views.decorators import staff_member_required
from ninja import NinjaAPI
from ninja.security import SessionAuth

api = NinjaAPI(
    title="DSA40 Application Helper",
    version="1.0.0",
    urls_namespace="api",
    auth=SessionAuth(),
    docs_decorator=staff_member_required,
)

api.add_router("/users/", "idat.users.api.views.router")
api.add_router("/v1/health", "idat.dsa40.api.views.health_router")
api.add_router("/v1/vlopse", "idat.vlopse.api.views.router")
api.add_router(
    "/v1/vlopse/{vlopse_name}/question",
    "idat.dsa40_form_handler.api.views.vlopse_question_router",
)
api.add_router("/v1/question", "idat.dsa40_form_handler.api.views.dsa_question_router")
api.add_router("/v1/", "idat.dsa40_form_handler.api.views.form_router")
