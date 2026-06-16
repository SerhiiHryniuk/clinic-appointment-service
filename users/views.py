from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema  # 1. Import the decorator
from users.serializers import UserSerializer


@extend_schema(tags=["Users"])  # 2. Tag for user registration
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)


@extend_schema(tags=["Users"])  # 3. Tag for the /me/ profile endpoints
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
