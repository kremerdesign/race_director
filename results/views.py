import re
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from forms import *
from django.core.mail import send_mail
from models import *


def home(request):
    upcoming_races = Race.objects.filter(date__gt=datetime.today())
    past_races = Race.objects.filter(date__lt=datetime.today())
    data = {
        'upcoming_races': upcoming_races,
        'past_races': past_races,
    }
    return render(request, "home.html", data)


@staff_member_required
def bulk_results(request):
    if request.method == 'POST':
        form = BulkCreateResults(request.POST)
        if form.is_valid():
            race = form.cleaned_data['race']
            results_data = form.cleaned_data['results']
            added_result = []
            for line in results_data.split('\n'):
                line = line.rstrip()
                if line == '' or line == ' ' or not line:
                    pass
                else:
                    # FINDING SETTING AND REMOVING AGE CLASS
                    m = re.search(r'BOY|BOYS|YM|JM|SM|MM|SMM|GIRL|GIRLS|YW|JW|SW|MW|SMW', line)
                    age_class = ""
                    if m:
                        age_class = m.group(0)
                        line = line.replace(age_class, "")
                    gender = get_gender(age_class)
                    # FINDING SETTING AND REMOVING PERCENT
                    m = re.search(r'(\d+\.\d+%)', line)
                    percent = ""
                    if m:
                        percent = m.group(0)
                        line = line.replace(percent, "")
                    # FINDING SETTING AND REMOVING MULTI
                    m = re.search(r'^([0-9]+)\s([0-9]+)?\s?(\S+\s+\S+)\s+([a-zA-Z \.\-]+) ', line)
                    name = "Empty Name"
                    all_captured = ""
                    bib_number = -1
                    club = ""
                    place = 999
                    if m:
                        place = m.group(1)
                        bib_number = m.group(2)
                        name = m.group(3)
                        club = m.group(4)
                        all_captured = m.group()
                    racer, created = Racer.objects.get_or_create(name=name, gender=gender)
                    line = line.replace(all_captured, "")
                    # FINDING TIMES
                    m = re.findall(r'(\d+:?\d+:\d+[\.]?[\d]?)', line) #return list of times
                    finish_time = median(m)
                    for item in m:
                        line = line.replace(str(item), "")

                    # shooting scores
                    first_shoot = -1
                    second_shoot = -1
                    third_shoot = -1
                    fourth_shoot = -1
                    all_shooting = -1
                    line = line.replace(" ", "")
                    # m = re.findall(r'[ \-]([0-5])', line)
                    num_of_shooting = len(line)
                    if num_of_shooting % 2 == 1:
                        num_of_shooting -= 1
                    if m:
                        # all_shooting = m.group()
                        first_shoot = line[0]
                        second_shoot = line[1]
                        if num_of_shooting > 2:
                            third_shoot = line[2]
                            fourth_shoot = line[3]
                    # line = line.replace(all_shooting, "")
                    # finish_time = line
                    result = Result.objects.create(race=race, racer=racer, place=place,
                                          start_time='0:00:00', finish_time=finish_time,
                                          first_shoot=first_shoot, second_shoot=second_shoot,
                                          third_shoot=third_shoot, fourth_shoot=fourth_shoot,)

                    added_result.append(result)
            new_form = BulkCreateResults()
            return render(request, "result/bulk_add_results.html", {
                'added_results': added_result, 'form': new_form,
            })
    else:
        form = BulkCreateResults()
    return render(request, "result/bulk_add_results.html", {
        'form': form,
    })


"""
USER PROFILES
"""

def register(request):
    if request.method == 'POST':
        form = RaceUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect("profile")
    else:
        form = RaceUserCreationForm()
    return render(request, "registration/register.html", {
        'form': form,
    })


@login_required
def profile(request):
    data = {
        'user': request.user,
    }
    return render(request, 'profile/profile.html', data)


@login_required
def profile_update(request, user_id):
    user = User.objects.get(id=user_id)
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = UserForm(instance=user)
    data = {"user": request.user, "form": form}
    return render(request, "profile/profile_update.html", data)


"""
CLUBS
"""

def clubs(request):
    #list all clubs
    clubs = Club.objects.all()
    return render(request, "club/clubs.html", {'clubs': clubs})

def view_club(request, club_id):
    #individual club listing
    club = Club.objects.get(id=club_id)
    data = {"club": club}
    return render(request, "club/view_club.html", data)

def new_club(request):
    # add club
    if request.method == "POST":
        # Get the instance of the form filled with the submitted data
        form = ClubForm(request.POST)
        # Django will check the form's validity for you
        if form.is_valid():
            # Saving the form will create a new Club object
            if form.save():
                # After saving, redirect the user back to the index page
                return redirect("/clubs")
    # Else if the user is looking at the form page
    else:
        form = ClubForm()
    data = {'form': form}
    return render(request, "club/new_club.html", data)

@staff_member_required
def edit_club(request, club_id):
    club = Club.objects.get(id=club_id)
    if request.method == "POST":
        # We prefill the form by passing 'instance', which is the specific
        # object we are editing
        form = ClubForm(request.POST, instance=club)
        if form.is_valid():
            if form.save():
                return redirect("/clubs/{}".format(club_id))
    # Or just viewing the form
    else:
        # We prefill the form by passing 'instance', which is the specific
        # object we are editing
        form = ClubForm(instance=club)
    data = {"club": club, "form": form}
    return render(request, "club/edit_club.html", data)

@staff_member_required
def delete_club(request, club_id):
    club = Club.objects.get(id=club_id)
    club.delete()
    return redirect("/clubs")


"""
RACES
"""

def races(request):
    #list all races
    all_races = Race.objects.all()
    return render(request, "race/races.html", {'races': all_races})

def view_race(request, race_id):
    #individual race listing
    race = Race.objects.get(id=race_id)
    data = {"race": race}
    return render(request, "race/view_race.html", data)

def new_race(request):
    # add race
    if request.method == "POST":
        form = RaceForm(request.POST)
        if form.is_valid():
            if form.save():
                return redirect("/races")
    else:
        form = RaceForm()
    data = {'form': form}
    return render(request, "race/new_race.html", data)

@staff_member_required
def edit_race(request, race_id):
    race = Race.objects.get(id=race_id)
    if request.method == "POST":
        form = RaceForm(request.POST, instance=race)
        if form.is_valid():
            if form.save():
                return redirect("/races/{}".format(race_id))
    else:
        form = RaceForm(instance=race)
    data = {"race": race, "form": form}
    return render(request, "race/edit_race.html", data)

@staff_member_required
def delete_race(request, race_id):
    race = Race.objects.get(id=race_id)
    race.delete()
    return redirect("/races")


"""
RACERS
"""
def racers(request):
    #list all racers
    racers = Racer.objects.all()
    return render(request,"racer/racers.html", {'racers': racers})

def view_racer(request, racer_id):
    #individual racer listing
    results = Result.objects.filter(racer_id=racer_id)
    racer = Racer.objects.get(id=racer_id)
    # all_results = Result.objects.all()
    data = {
        "racer": racer,
        "results": results,
        # "all_results": all_results
    }
    return render(request, "racer/view_racer.html", data)

def new_racer(request):
    # add racer
    if request.method == "POST":
        form = RacerForm(request.POST)
        if form.is_valid():
            if form.save():
                return redirect("/racers")
    else:
        form = RacerForm()
    data = {'form': form}
    return render(request, "racer/new_racer.html", data)

@staff_member_required
def edit_racer(request, racer_id):
    racer = Racer.objects.get(id=racer_id)
    if request.method == "POST":
        form = RacerForm(request.POST, instance=racer)
        if form.is_valid():
            if form.save():
                return redirect("/racers/{}".format(racer_id))
    else:
        form = RacerForm(instance=racer)
    data = {"racer": racer, "form": form}
    return render(request, "racer/edit_racer.html", data)

@staff_member_required
def delete_racer(request, racer_id):
    racer = Racer.objects.get(id=racer_id)
    racer.delete()
    return redirect("/racers")


"""
RESULTS
"""
def results(request):
    #list all results
    past_races = Race.objects.filter(date__lt=datetime.today())
    # results = Result.objects.all()
    return render(request, "result/results.html", {'past_races': past_races})

def view_result(request, result_id):
    #individual result listing
    result = Result.objects.get(id=result_id)
    data = {"result": result}
    return render(request, "result/view_results.html", data)

def view_race_results(request, race_id):
    #individual result listing
    race = Race.objects.get(id=race_id)
    # racers = Racer.objects.filter(race__pk=race_id).all()
    results = Result.objects.filter(race__pk=race_id).all()
    data = {"race": race, "results": results}
    return render(request, "result/view_race_results.html", data)


def new_result(request):
    # add result
    if request.method == "POST":
        form = ResultForm(request.POST)
        if form.is_valid():
            if form.save():
                return redirect("/results")
    else:
        form = ResultForm()
    data = {'form': form}
    return render(request, "result/new_result.html", data)

@staff_member_required
def edit_result(request, result_id):
    result = Result.objects.get(id=result_id)
    if request.method == "POST":
        form = ResultForm(request.POST, instance=result)
        if form.is_valid():
            if form.save():
                return redirect("/results/{}".format(result_id))
    else:
        form = ResultForm(instance=result)
    data = {"result": result, "form": form}
    return render(request, "result/edit_result.html", data)

@staff_member_required
def delete_result(request, result_id):
    result = Result.objects.get(id=result_id)
    result.delete()
    return redirect("/results")


def get_gender(value):
    if any(value in s for s in ['GIRL','GIRLS','YW','JW','SW','MW','SMW','W','F','G']):
        return 'F'
    else:
        return 'M'

def num_groups(regex):
    return re.compile(regex).groups

def find_finish_time(times):
    result = '8:88:88'
    times = sorted(times)

def median(lst):
    new_lst = []
    for item in lst:
        if item.count(':') == 1:
            item = '0:' + item
        new_lst.append(item)
    even = (0 if len(new_lst) % 2 else 1) + 1
    half = (len(new_lst) - 1) / 2
    return sorted(new_lst)[int(half):int((half + even)/ float(even))][0]
