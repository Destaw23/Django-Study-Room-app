from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.views.decorators.http import require_POST
from .models import Profile, Room, Topic ,Message
from .forms import RegisterForm, RoomForm , UserForm

def loginpage(request):
    page='login'
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request,user)
            return redirect('home')
        else:
            messages.error(request,'Username or password is incorrect.')

    context={'page':page}
    return render(request,'base/login_register.html',context)

@require_POST
def logoutUser(request):
    logout(request)
    return redirect('home')

def registerpage(request):
  
    form = RegisterForm()
    if request.method == "POST":
        form=RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user=form.save(commit=False)
            user.save() 
            Profile.objects.create(user=user, avatar=form.cleaned_data.get('avatar'))
            login(request,user)
            return redirect('home')   
        else:
            messages.error(request,'An error occured during registration')     

    return render(request,'base/login_register.html',{'form':form})

def home(request):
    q = request.GET.get('q') if request.GET.get('q') !=None else ''
    rooms = Room.objects.select_related('host', 'topic').prefetch_related(
        'participants'
    ).filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q) 
        )
    topics = Topic.objects.all()[0:5]
    room_count = rooms.count()
    room_messages = Message.objects.select_related(
        'user', 'user__profile', 'room'
    ).filter(Q(room__topic__name__icontains=q))

    context = {'rooms':rooms , 'topics': topics, 
               'room_count':room_count , 'room_messages':room_messages}
    return render(request,'base/home.html',context)
def userProfile(request,pk):
    user = get_object_or_404(User, id=pk)
    rooms = user.room_set.select_related('host', 'topic').prefetch_related(
        'participants'
    )
    room_messages = user.message_set.select_related('user', 'user__profile', 'room')
    topics =Topic.objects.all()
    context ={'user':user, 'rooms':rooms, 'room_messages':room_messages,'topics':topics}
    return render(request, 'base/profile.html', context)


def room(request,pk):
    room = get_object_or_404(Room, id=pk)
    room_messages = room.message_set.select_related('user', 'user__profile')
    participants = room.participants.select_related('profile')
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='login')

        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'A message cannot be empty.')
            return redirect('room', pk=room.id)

        Message.objects.create(
            user = request.user,
            room=room,
            body=body

        )
        room.participants.add(request.user)
        return redirect('room',pk=room.id)

    context ={'room':room,'room_messages':room_messages,'participants':participants}     
    return render(request,'base/room.html',context)

@login_required(login_url='login')
def createRoom(request):
    form = RoomForm()
    topics=Topic.objects.all()
    if request.method =='POST':
        topic_name = request.POST.get('topic')
        topic,created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
        )
        return redirect('home')
    context= {'form': form, 'topics':topics}
    return render(request, 'base/room_form.html',context)

@login_required(login_url='login')
def updateRoom(request,pk):
    room = get_object_or_404(Room, id=pk)
    form = RoomForm(instance=room)
    topics=Topic.objects.all()

    if request.user !=room.host:
        raise PermissionDenied
    
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic,created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')

    context = {'form': form, 'topics':topics, 'room':room}
    return render(request,'base/room_form.html', context)

@login_required(login_url='login')
def deleteRoom(request,pk):
    room = get_object_or_404(Room, id=pk)
    if request.user !=room.host:
        raise PermissionDenied
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html',{'obj':room})

@login_required(login_url='login')
def deleteMessage(request,pk):
    message = get_object_or_404(Message, id=pk)
    if request.user !=message.user:
        raise PermissionDenied
    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html',{'obj':message})

@login_required(login_url='login')
def updateUser(request):
    user=request.user
    form = UserForm(instance=user)
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile',pk=user.id)
    return render(request,'base/update-user.html', {'form':form, })

def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') !=None else ''

    topics = Topic.objects.filter(name__icontains=q)
    return render(request, 'base/topics.html', {'topics':topics})

def activityPage(request):
    room_messages = Message.objects.select_related(
        'user', 'user__profile', 'room'
    )
    return render(request,'base/activity.html', {'room_messages':room_messages})
