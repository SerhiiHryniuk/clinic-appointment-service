from rest_framework_simplejwt.authentication import JWTAuthentication


class CustomJWTAuthentication(JWTAuthentication):
    def get_header(self, request):
        header = request.META.get("HTTP_AUTHORIZE")
        if isinstance(header, str):
            header = header.encode("iso-8859-1")
        return header
