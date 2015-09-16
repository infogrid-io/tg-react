from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model

from .serializers import (
        AuthenticationSerializer, UserDetailsSerializer, SSerializer, ForgotPasswordSerializer,
        RecoveryPasswordSerializer)

# for email notifications
from django.template.loader import get_template
from django.template import Context

from django.utils.translation import ugettext as _

from settings.base import SITE_URL


class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        pass


class UserDetails(generics.RetrieveAPIView):
    serializer_class = UserDetailsSerializer
    authentication_classes = (SessionAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get_object(self):
        return self.request.user


class AuthenticationView(APIView):
    class UnsafeSessionAuthentication(SessionAuthentication):
        def enforce_csrf(self, request):
            pass

    throttle_classes = ()
    permission_classes = (AllowAny,)
    authentication_classes = (UnsafeSessionAuthentication, )
    serializer_class = AuthenticationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA)
        if serializer.is_valid():
            from django.contrib.auth import login
            login(request, serializer.user)

            return Response({'success': True})

        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    throttle_classes = ()
    permission_classes = (IsAuthenticated, )
    authentication_classes = (SessionAuthentication, )

    def post(self, request):
        from django.contrib.auth import logout
        logout(request)

        return Response({'success': True})


class SignUpView(APIView):
    serializer_class = SSerializer
    permission_classes = (AllowAny, )
    authentication_classes = (UnsafeSessionAuthentication, )

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA, context={'request': request})
        if serializer.is_valid():
            data = serializer.validated_data.copy()
            password = data.pop('password', None)

            user = get_user_model()(**data)
            user.set_password(password)
            user.save()

            from django.contrib.auth import login, authenticate
            user = authenticate(email=data['email'], password=password)
            login(request, user)

            return Response({'success': True})

        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ForgotPassword(APIView):
    """
    Initiate a password restore procedure.
    """

    # Example request data
    # {
    #   "email" : "chuvak2353@gmail.com"
    # }

    serializer_class = ForgotPasswordSerializer
    authentication_classes = (UnsafeSessionAuthentication, )
    permission_classes = (AllowAny, )

    def send_email_notification(self, user, uid_and_token_b64):
        # define email notification logic
        from django.core.mail import EmailMultiAlternatives
        # make confirm reset url
        confirm_reset_url = '%s/reset_password/%s' % (SITE_URL, uid_and_token_b64)

        subject = _("Password restore")
        context = Context({'user': user, 'confirm_reset_url': confirm_reset_url})
        text_content = get_template('emails/password_reset.txt').render(context)
        html_content = get_template('emails/password_reset.html').render(context)

        msg = EmailMultiAlternatives(subject, text_content, to=[user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA)
        if serializer.is_valid():
            self.send_email_notification(serializer.user, serializer.validated_data['uid_and_token_b64'])
            return Response({'success': True})

        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class RestorePassword(APIView):
    """
    Validate token and change a user password.
    """

    # Example request data
    # {
    #   "password" : "asdasd",
    #   "password_confirm" : "asdasd",
    #   "uid_and_token_b64" : "eyJ1aWQiOiAxLCAidG9rZW4iOiAiNDN1LWY5ZDIyMmM4YTNkZDhmYjI2OThlIn0="
    # }

    serializer_class = RecoveryPasswordSerializer
    authentication_classes = (UnsafeSessionAuthentication, )
    permission_classes = (AllowAny, )

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA)
        if serializer.is_valid():
            user = serializer.user
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({'success': True})

        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
