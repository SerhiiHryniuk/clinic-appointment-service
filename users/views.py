from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema  # 1. Import the decorator
from users.serializers import UserSerializer


@extend_schema(tags=["Users"])
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)


@extend_schema(tags=["Users"])
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
