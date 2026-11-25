from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Profile, Room


def validate_avatar_size(image):
    if image.size > 5 * 1024 * 1024:
        raise ValidationError('Profile images must be 5 MB or smaller.')


class RegisterForm(UserCreationForm):
    avatar = forms.ImageField(required=False, validators=[validate_avatar_size])

    def clean_username(self):
        username = self.cleaned_data['username'].lower()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                'A user with that username already exists.',
                code='duplicate',
            )
        return username


class UserForm(ModelForm):
    avatar = forms.ImageField(required=False, validators=[validate_avatar_size])
    bio = forms.CharField(
        label='About',
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 4,
                'placeholder': 'Write a little about yourself',
            }
        ),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'avatar', 'bio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            profile = Profile.objects.filter(user=self.instance).only('bio').first()
            if profile:
                self.fields['bio'].initial = profile.bio

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = Profile.objects.get_or_create(user=user)
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                profile.avatar = avatar
            if self.add_prefix('bio') in self.data:
                profile.bio = self.cleaned_data['bio']
            profile.save()
        return user


class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        exclude=['host','participants']
