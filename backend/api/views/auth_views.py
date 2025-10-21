from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import sentry_sdk
import logging
from ..serializers import (
	UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer, GoogleAuthSerializer
)
from ..models import User
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests as http_requests

logger = logging.getLogger(__name__)


class RegisterView(APIView):
	"""
	API view to handle user registration.
	"""
	permission_classes = [AllowAny]
	serializer_class = UserRegistrationSerializer

	def post(self, request):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			refresh = RefreshToken.for_user(user)
			return Response({
				'user': UserProfileSerializer(user).data,
				'refresh': str(refresh),
				'access': str(refresh.access_token),
			}, status=status.HTTP_201_CREATED)
		# Log validation errors for easier debugging
		if serializer.errors:
			logger.warning('Registration validation errors: %s', serializer.errors)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
	"""
	API view to handle user login.
	"""
	permission_classes = [AllowAny]
	serializer_class = UserLoginSerializer

	def post(self, request):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid():
			user = serializer.validated_data['user']
			refresh = RefreshToken.for_user(user)
			return Response({
				'user': UserProfileSerializer(user).data,
				'refresh': str(refresh),
				'access': str(refresh.access_token),
			})
		# Log validation errors for debugging
		logger.error(f'Login validation errors: {serializer.errors}')
		logger.error(f'Login request data: {request.data}')
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
	"""
	API view to handle user profile.
	"""
	permission_classes = [IsAuthenticated]

	def get(self, request):
		serializer = UserProfileSerializer(request.user)
		return Response(serializer.data)

	def put(self, request):
		serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleAuthView(APIView):
	"""
	API view to handle Google OAuth authentication.
	Supports both ID token (OpenID Connect) and access token (OAuth 2.0) flows.
	"""
	permission_classes = [AllowAny]

	def post(self, request):
		try:
			credential = request.data.get('credential')

			if not credential:
				return Response({'error': 'No credential provided'}, status=status.HTTP_400_BAD_REQUEST)

			try:
				idinfo = id_token.verify_oauth2_token(
					credential,
					google_requests.Request(),
					settings.GOOGLE_OAUTH_CLIENT_ID
				)
				if idinfo['aud'] != settings.GOOGLE_OAUTH_CLIENT_ID:
					return Response({'error': 'Invalid token audience'}, status=status.HTTP_400_BAD_REQUEST)
				email = idinfo.get('email')
				name = idinfo.get('name', '')
				google_id = idinfo.get('sub')
			except ValueError:
				try:
					response = http_requests.get(
						'https://www.googleapis.com/oauth2/v2/userinfo',
						headers={'Authorization': f'Bearer {credential}'},
						timeout=10
					)
					if response.status_code != 200:
						return Response({'error': 'Failed to verify access token'}, status=status.HTTP_400_BAD_REQUEST)
					user_info = response.json()
					email = user_info.get('email')
					name = user_info.get('name', '')
					google_id = user_info.get('id')
				except Exception as access_token_error:
					sentry_sdk.capture_exception(access_token_error, extras={
						"component": "auth",
						"view": "GoogleAuthView",
						"error_type": "access_token_verification_failed"
					})
					return Response({'error': f'Invalid credential: {str(access_token_error)}'}, status=status.HTTP_400_BAD_REQUEST)

			if not email:
				return Response({'error': 'Email not provided by Google'}, status=status.HTTP_400_BAD_REQUEST)

			user, created = User.objects.get_or_create(
				email=email,
				defaults={
					'username': email.split('@')[0],
					'name': name,
					'google_id': google_id,
					'is_active': True,
				}
			)

			if not created and not user.google_id:
				user.google_id = google_id
				user.save()

			refresh = RefreshToken.for_user(user)

			return Response({
				'user': UserProfileSerializer(user).data,
				'refresh': str(refresh),
				'access': str(refresh.access_token),
				'message': 'Login successful' if not created else 'Account created successfully'
			})

		except Exception as e:
			sentry_sdk.capture_exception(e, extras={"component": "auth", "view": "GoogleAuthView"})
			return Response({'error': f'Authentication failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


__all__ = ['RegisterView', 'LoginView', 'ProfileView', 'GoogleAuthView']
