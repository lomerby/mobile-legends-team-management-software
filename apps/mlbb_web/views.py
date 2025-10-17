import requests
import os
import json
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from functools import wraps
from typing import Dict

from .models import DraftSession, Team, HeroPick, HeroBan, DraftTemplate, DraftNote
from .services import MLBBAPIService, DraftRecommendationService

PROD_URL = settings.PROD_URL

HERO_NAME_DICT = {
    129: "Zetian", 128: "Kalea", 127: "Lukas", 126: "Suyou", 125: "Zhuxin", 124: "Chip", 123: "Cici", 122: "Nolan", 121: "Ixia", 120: "Arlott", 119: "Novaria",
    118: "Joy", 117: "Fredrinn", 116: "Julian", 115: "Xavier", 114: "Melissa", 113: "Yin", 112: "Floryn",
    111: "Edith", 110: "Valentina", 109: "Aamon", 108: "Aulus", 107: "Natan", 106: "Phoveus", 105: "Beatrix",
    104: "Gloo", 103: "Paquito", 102: "Mathilda", 101: "Yve", 100: "Brody", 99: "Barats", 98: "Khaleed",
    97: "Benedetta", 96: "Luo Yi", 95: "Yu Zhong", 94: "Popol and Kupa", 93: "Atlas", 92: "Carmilla",
    91: "Cecilion", 90: "Silvanna", 89: "Wanwan", 88: "Masha", 87: "Baxia", 86: "Lylia", 85: "Dyrroth",
    84: "Ling", 83: "X.Borg", 82: "Terizla", 81: "Esmeralda", 80: "Guinevere", 79: "Granger", 78: "Khufra",
    77: "Badang", 76: "Faramis", 75: "Kadita", 74: "Minsitthar", 73: "Harith", 72: "Thamuz", 71: "Kimmy",
    70: "Belerick", 69: "Hanzo", 68: "Lunox", 67: "Leomord", 66: "Vale", 65: "Claude", 64: "Aldous",
    63: "Selena", 62: "Kaja", 61: "Chang'e", 60: "Hanabi", 59: "Uranus", 58: "Martis", 57: "Valir",
    56: "Gusion", 55: "Angela", 54: "Jawhead", 53: "Lesley", 52: "Pharsa", 51: "Helcurt", 50: "Zhask",
    49: "Hylos", 48: "Diggie", 47: "Lancelot", 46: "Odette", 45: "Argus", 44: "Grock", 43: "Irithel",
    42: "Harley", 41: "Gatotkaca", 40: "Karrie", 39: "Roger", 38: "Vexana", 37: "Lapu-Lapu", 36: "Aurora",
    35: "Hilda", 34: "Estes", 33: "Cyclops", 32: "Johnson", 31: "Moskov", 30: "Yi Sun-shin", 29: "Ruby",
    28: "Alpha", 27: "Sun", 26: "Chou", 25: "Kagura", 24: "Natalia", 23: "Gord", 22: "Freya", 21: "Hayabusa",
    20: "Lolita", 19: "Minotaur", 18: "Layla", 17: "Fanny", 16: "Zilong", 15: "Eudora", 14: "Rafaela",
    13: "Clint", 12: "Bruno", 11: "Bane", 10: "Franco", 9: "Akai", 8: "Karina", 7: "Alucard", 6: "Tigreal",
    5: "Nana", 4: "Alice", 3: "Saber", 2: "Balmond", 1: "Miya"
}

def web_availability_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not settings.IS_AVAILABLE:
            status_info = settings.API_STATUS_MESSAGES['limited']
            return JsonResponse({
                'error': 'Service Unavailable',
                'status': status_info['status'],
                'message': status_info['message'],
                'available_endpoints': ['Home page only']
            }, status=503)
        return view_func(request, *args, **kwargs)
    return wrapper

class MLBBWebService:
    @staticmethod
    def get_json(url):
        response = requests.get(url)
        if response.status_code != 200:
            return None
        return response.json()

    @staticmethod
    def multiply_rates(record, fields):
        for field in fields:
            if field in record:
                record[field] *= 100

    @staticmethod
    def round_rates(record, fields):
        for field in fields:
            if field in record:
                record[field] = round(record[field] * 100, 2)

    @staticmethod
    def map_hero_ids(record, relation_types):
        for relation_type in relation_types:
            for i, hero_id in enumerate(record['data']['relation'][relation_type]['target_hero_id']):
                record['data']['relation'][relation_type]['target_hero_id'][i] = (
                    HERO_NAME_DICT.get(hero_id, 'Unknown') if hero_id != 0 else 'Unknown'
                )

    @staticmethod
    def rename_skill_fields(skilllist):
        for skill in skilllist:
            for skill_detail in skill['skilllist']:
                if 'skillcd&cost' in skill_detail:
                    skill_detail['skillcd_cost'] = skill_detail.pop('skillcd&cost')

    @staticmethod
    def rename_recommendmasterplan_fields(planlist):
        for plan in planlist:
            if '__data' in plan['battleskill']:
                plan['battleskill']['data'] = plan['battleskill'].pop('__data')

    @staticmethod
    def process_sub_hero_rates(sub_hero_list):
        for sub_hero in sub_hero_list:
            MLBBWebService.round_rates(sub_hero, ['hero_appearance_rate', 'hero_win_rate', 'increase_win_rate'])

def favicon_view(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'favicon.ico')
    if os.path.exists(favicon_path):
        return FileResponse(open(favicon_path, 'rb'), content_type='image/x-icon')
    else:
        raise Http404('Favicon not found')

class MLBBWebViews:
    @staticmethod
    @web_availability_required
    def hero_list_web(request):
        data = MLBBWebService.get_json(f'{PROD_URL}hero-list-new/')
        return render(request, 'mlbb_web/hero-list.html', {'data': data})

    @staticmethod
    @web_availability_required
    def hero_rank_web(request):
        days = request.GET.get('days', '1')
        rank = request.GET.get('rank', 'all')
        size = request.GET.get('size', '20')
        index = request.GET.get('index', '1')
        sort_field = request.GET.get('sort_field', 'win_rate')
        sort_order = request.GET.get('sort_order', 'desc')

        url = f'{PROD_URL}hero-rank/?days={days}&rank={rank}&size={size}&index={index}&sort_field={sort_field}&sort_order={sort_order}'
        data = MLBBWebService.get_json(url)
        if not data or 'data' not in data or 'records' not in data['data']:
            return JsonResponse({'error': 'Data not found'}, status=404)

        for record in data['data']['records']:
            MLBBWebService.multiply_rates(record['data'], [
                'main_hero_appearance_rate', 'main_hero_ban_rate', 'main_hero_win_rate'
            ])
            for sub_hero in record['data']['sub_hero']:
                sub_hero['increase_win_rate'] *= 100

        return render(request, 'mlbb_web/hero-rank.html', {
            'data': data,
            'days': days,
            'rank': rank,
            'size': size,
            'index': index,
            'sort_field': sort_field,
            'sort_order': sort_order
        })

    @staticmethod
    @web_availability_required
    def hero_position_web(request):
        role = request.GET.get('role', 'all')
        lane = request.GET.get('lane', 'all')
        size = request.GET.get('size', '21')
        index = request.GET.get('index', '1')

        url = f'{PROD_URL}hero-position/?role={role}&lane={lane}&size={size}&index={index}'
        data = MLBBWebService.get_json(url)
        if data and data['data']['records'] is not None:
            for record in data['data']['records']:
                MLBBWebService.map_hero_ids(record, ['assist', 'strong', 'weak'])

        return render(request, 'mlbb_web/hero-position.html', {
            'data': data,
            'role': role,
            'lane': lane,
            'size': size,
            'index': index
        })

    @staticmethod
    @web_availability_required
    def hero_detail_web(request, hero_id):
        # Hero detail
        data_hero_detail = MLBBWebService.get_json(f'{PROD_URL}hero-detail/{hero_id}/')
        if not data_hero_detail or 'data' not in data_hero_detail or 'records' not in data_hero_detail['data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        records_data_hero_detail = data_hero_detail['data']['records'][0]['data']

        MLBBWebService.rename_skill_fields(records_data_hero_detail['hero']['data']['heroskilllist'])
        MLBBWebService.rename_recommendmasterplan_fields(records_data_hero_detail['hero']['data']['recommendmasterplan'])

        # Hero stats
        data_hero_detail_stats = MLBBWebService.get_json(f'{PROD_URL}hero-detail-stats/{hero_id}/')
        if not data_hero_detail_stats or 'data' not in data_hero_detail_stats or 'records' not in data_hero_detail_stats['data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        for record_stats in data_hero_detail_stats['data']['records']:
            MLBBWebService.multiply_rates(record_stats['data'], [
                'main_hero_appearance_rate', 'main_hero_ban_rate', 'main_hero_win_rate'
            ])

        # Hero counter
        data_hero_counter = MLBBWebService.get_json(f'{PROD_URL}hero-counter/{hero_id}/')
        if not data_hero_counter or 'data' not in data_hero_counter or 'records' not in data_hero_counter['data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        for record in data_hero_counter['data']['records']:
            MLBBWebService.process_sub_hero_rates(record['data']['sub_hero'])
            MLBBWebService.process_sub_hero_rates(record['data']['sub_hero_last'])

        # Hero compatibility
        data_hero_compatibility = MLBBWebService.get_json(f'{PROD_URL}hero-compatibility/{hero_id}/')
        if not data_hero_compatibility or 'data' not in data_hero_compatibility or 'records' not in data_hero_compatibility['data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        for record in data_hero_compatibility['data']['records']:
            MLBBWebService.process_sub_hero_rates(record['data']['sub_hero'])
            MLBBWebService.process_sub_hero_rates(record['data']['sub_hero_last'])

        return render(request, 'mlbb_web/hero-detail.html', {
            'data': records_data_hero_detail,
            'stats': data_hero_detail_stats,
            'counter': data_hero_counter,
            'compatibility': data_hero_compatibility
        })

# Draft System Views
def draft_home(request):
    """Main drafting homepage"""
    recent_drafts = DraftSession.objects.filter(
        session_key=request.session.session_key
    )[:5] if not request.user.is_authenticated else DraftSession.objects.filter(
        user=request.user
    )[:5]
    
    templates = DraftTemplate.objects.filter(
        is_public=True
    ).order_by('-created_at')[:6]
    
    context = {
        'recent_drafts': recent_drafts,
        'templates': templates,
    }
    return render(request, 'draft/home.html', context)

def create_draft(request):
    """Create a new draft session"""
    if request.method == 'POST':
        draft_name = request.POST.get('name', 'New Draft')
        
        # Create draft session
        draft = DraftSession.objects.create(
            name=draft_name,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            turn_order=[
                # Standard ML draft order: Ban1, Ban1, Ban1, Ban1, Pick1, Pick1, Ban2, Ban2, Pick2, Pick2, Pick3, Pick3
                'blue_ban', 'red_ban', 'blue_ban', 'red_ban',  # Ban phase 1
                'blue_pick', 'red_pick',  # Pick phase 1
                'blue_ban', 'red_ban',  # Ban phase 2
                'red_pick', 'blue_pick',  # Pick phase 2 (reversed order)
                'red_pick', 'blue_pick', 'blue_pick', 'red_pick'  # Pick phase 3
            ]
        )
        
        # Create teams
        Team.objects.create(draft_session=draft, side='blue', name='Blue Team')
        Team.objects.create(draft_session=draft, side='red', name='Red Team')
        
        return redirect('draft_session', draft_id=draft.id)
    
    return render(request, 'draft/create.html')

def draft_session(request, draft_id):
    """Main draft session interface with API integration"""
    draft = get_object_or_404(DraftSession, id=draft_id)
    
    # Check access permissions
    if not request.user.is_authenticated and draft.session_key != request.session.session_key:
        messages.error(request, 'You do not have access to this draft session.')
        return redirect('draft_home')
    elif request.user.is_authenticated and draft.user != request.user and draft.session_key != request.session.session_key:
        messages.error(request, 'You do not have access to this draft session.')
        return redirect('draft_home')
    
    blue_team = draft.teams.get(side='blue')
    red_team = draft.teams.get(side='red')
    
    # Get current state
    current_action = 'completed' if draft.is_completed else (
        draft.turn_order[draft.current_turn_index] if draft.current_turn_index < len(draft.turn_order) else 'completed'
    )
    
    # Initialize API services
    api_service = MLBBAPIService()
    recommendation_service = DraftRecommendationService()
    
    # Get hero data from API
    heroes_data = api_service.get_hero_list()
    heroes_dict = {hero['id']: hero for hero in heroes_data}
    
    # Get current picks and bans
    blue_picks = [p.hero_id for p in blue_team.picks.all()]
    red_picks = [p.hero_id for p in red_team.picks.all()]
    all_bans = [b.hero_id for b in HeroBan.objects.filter(team__draft_session=draft)]
    
    # Get recommendations if draft is not completed
    recommendations = []
    if not draft.is_completed and current_action != 'completed':
        if 'pick' in current_action:
            current_team_picks = blue_picks if 'blue' in current_action else red_picks
            enemy_picks = red_picks if 'blue' in current_action else blue_picks
            recommendations = recommendation_service.get_pick_recommendations(
                current_team_picks, all_bans, enemy_picks, 'pick'
            )
        elif 'ban' in current_action:
            enemy_picks = red_picks if 'blue' in current_action else blue_picks
            recommendations = recommendation_service.get_ban_recommendations(
                enemy_picks, all_bans
            )
    
    # Analyze team compositions
    blue_analysis = recommendation_service.analyze_team_composition(blue_picks)
    red_analysis = recommendation_service.analyze_team_composition(red_picks)
    
    context = {
        'draft': draft,
        'blue_team': blue_team,
        'red_team': red_team,
        'current_action': current_action,
        'heroes': HERO_NAME_DICT,
        'heroes_data': heroes_dict,
        'recommendations': recommendations,
        'blue_analysis': blue_analysis,
        'red_analysis': red_analysis,
        'progress': {
            'total_turns': len(draft.turn_order),
            'current_turn': draft.current_turn_index + 1
        }
    }
    return render(request, 'draft/session.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def draft_action(request, draft_id):
    """Handle pick/ban actions"""
    draft = get_object_or_404(DraftSession, id=draft_id)
    
    # Check access permissions
    if not request.user.is_authenticated and draft.session_key != request.session.session_key:
        return JsonResponse({'error': 'Access denied'}, status=403)
    elif request.user.is_authenticated and draft.user != request.user and draft.session_key != request.session.session_key:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if draft.is_completed:
        return JsonResponse({'error': 'Draft is already completed'}, status=400)
    
    data = json.loads(request.body)
    action_type = data.get('action')  # 'pick' or 'ban'
    hero_id = int(data.get('hero_id'))
    hero_name = data.get('hero_name', HERO_NAME_DICT.get(hero_id, f'Hero {hero_id}'))
    position = data.get('position')  # Only for picks
    
    if draft.current_turn_index >= len(draft.turn_order):
        return JsonResponse({'error': 'Draft is completed'}, status=400)
    
    current_turn = draft.turn_order[draft.current_turn_index]
    
    # Validate action matches current turn
    if action_type == 'pick' and 'pick' not in current_turn:
        return JsonResponse({'error': 'Not a pick phase'}, status=400)
    if action_type == 'ban' and 'ban' not in current_turn:
        return JsonResponse({'error': 'Not a ban phase'}, status=400)
    
    # Get the team
    team_side = current_turn.split('_')[0]  # 'blue' or 'red'
    team = draft.teams.get(side=team_side)
    
    # Check if hero is already picked or banned
    all_picks = HeroPick.objects.filter(team__draft_session=draft, hero_id=hero_id)
    all_bans = HeroBan.objects.filter(team__draft_session=draft, hero_id=hero_id)
    
    if all_picks.exists() or all_bans.exists():
        return JsonResponse({'error': 'Hero is already picked or banned'}, status=400)
    
    try:
        if action_type == 'pick':
            pick_order = team.picks.count() + 1
            HeroPick.objects.create(
                team=team,
                hero_id=hero_id,
                hero_name=hero_name,
                position=position,
                pick_order=pick_order
            )
        else:  # ban
            ban_order = team.bans.count() + 1
            HeroBan.objects.create(
                team=team,
                hero_id=hero_id,
                hero_name=hero_name,
                ban_order=ban_order
            )
        
        # Advance to next turn
        draft.current_turn_index += 1
        
        # Check if draft is completed
        if draft.current_turn_index >= len(draft.turn_order):
            draft.is_completed = True
            draft.current_phase = 'completed'
        
        draft.save()
        
        return JsonResponse({
            'success': True,
            'next_turn': draft.turn_order[draft.current_turn_index] if draft.current_turn_index < len(draft.turn_order) else 'completed',
            'is_completed': draft.is_completed,
            'progress': {
                'total_turns': len(draft.turn_order),
                'current_turn': draft.current_turn_index if not draft.is_completed else len(draft.turn_order)
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def draft_data(request, draft_id):
    """Get current draft data as JSON"""
    draft = get_object_or_404(DraftSession, id=draft_id)
    
    blue_team = draft.teams.get(side='blue')
    red_team = draft.teams.get(side='red')
    
    data = {
        'draft': {
            'id': draft.id,
            'name': draft.name,
            'is_completed': draft.is_completed,
            'current_turn_index': draft.current_turn_index,
            'total_turns': len(draft.turn_order),
            'current_action': draft.turn_order[draft.current_turn_index] if draft.current_turn_index < len(draft.turn_order) else 'completed'
        },
        'blue_team': {
            'name': blue_team.name,
            'picks': [{
                'hero_id': pick.hero_id,
                'hero_name': pick.hero_name,
                'position': pick.position,
                'pick_order': pick.pick_order
            } for pick in blue_team.picks.all()],
            'bans': [{
                'hero_id': ban.hero_id,
                'hero_name': ban.hero_name,
                'ban_order': ban.ban_order
            } for ban in blue_team.bans.all()]
        },
        'red_team': {
            'name': red_team.name,
            'picks': [{
                'hero_id': pick.hero_id,
                'hero_name': pick.hero_name,
                'position': pick.position,
                'pick_order': pick.pick_order
            } for pick in red_team.picks.all()],
            'bans': [{
                'hero_id': ban.hero_id,
                'hero_name': ban.hero_name,
                'ban_order': ban.ban_order
            } for ban in red_team.bans.all()]
        }
    }
    
    return JsonResponse(data)

def save_template(request, draft_id):
    """Save current draft as template"""
    if request.method == 'POST':
        draft = get_object_or_404(DraftSession, id=draft_id)
        
        # Check access permissions
        if not request.user.is_authenticated and draft.session_key != request.session.session_key:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        template_name = request.POST.get('name', f'{draft.name} Template')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public') == 'on'
        
        blue_team = draft.teams.get(side='blue')
        red_team = draft.teams.get(side='red')
        
        template = DraftTemplate.objects.create(
            name=template_name,
            description=description,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            is_public=is_public,
            blue_picks=[{
                'hero_id': pick.hero_id,
                'hero_name': pick.hero_name,
                'position': pick.position
            } for pick in blue_team.picks.all()],
            red_picks=[{
                'hero_id': pick.hero_id,
                'hero_name': pick.hero_name,
                'position': pick.position
            } for pick in red_team.picks.all()],
            blue_bans=[{
                'hero_id': ban.hero_id,
                'hero_name': ban.hero_name
            } for ban in blue_team.bans.all()],
            red_bans=[{
                'hero_id': ban.hero_id,
                'hero_name': ban.hero_name
            } for ban in red_team.bans.all()]
        )
        
        messages.success(request, f'Template "{template_name}" saved successfully!')
        return JsonResponse({'success': True, 'template_id': template.id})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def get_recommendations(request, draft_id):
    """Get real-time draft recommendations"""
    draft = get_object_or_404(DraftSession, id=draft_id)
    
    # Check access permissions
    if not request.user.is_authenticated and draft.session_key != request.session.session_key:
        return JsonResponse({'error': 'Access denied'}, status=403)
    elif request.user.is_authenticated and draft.user != request.user and draft.session_key != request.session.session_key:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if draft.is_completed:
        return JsonResponse({'recommendations': []})
    
    blue_team = draft.teams.get(side='blue')
    red_team = draft.teams.get(side='red')
    
    blue_picks = [p.hero_id for p in blue_team.picks.all()]
    red_picks = [p.hero_id for p in red_team.picks.all()]
    all_bans = [b.hero_id for b in HeroBan.objects.filter(team__draft_session=draft)]
    
    current_action = draft.turn_order[draft.current_turn_index] if draft.current_turn_index < len(draft.turn_order) else 'completed'
    
    recommendation_service = DraftRecommendationService()
    recommendations = []
    
    if 'pick' in current_action:
        current_team_picks = blue_picks if 'blue' in current_action else red_picks
        enemy_picks = red_picks if 'blue' in current_action else blue_picks
        recommendations = recommendation_service.get_pick_recommendations(
            current_team_picks, all_bans, enemy_picks, 'pick'
        )
    elif 'ban' in current_action:
        enemy_picks = red_picks if 'blue' in current_action else blue_picks
        recommendations = recommendation_service.get_ban_recommendations(
            enemy_picks, all_bans
        )
    
    return JsonResponse({
        'recommendations': recommendations,
        'current_action': current_action,
        'phase': 'pick' if 'pick' in current_action else 'ban'
    })

def draft_analytics(request, draft_id):
    """Get draft analytics and team composition analysis"""
    draft = get_object_or_404(DraftSession, id=draft_id)
    
    blue_team = draft.teams.get(side='blue')
    red_team = draft.teams.get(side='red')
    
    blue_picks = [p.hero_id for p in blue_team.picks.all()]
    red_picks = [p.hero_id for p in red_team.picks.all()]
    
    recommendation_service = DraftRecommendationService()
    blue_analysis = recommendation_service.analyze_team_composition(blue_picks)
    red_analysis = recommendation_service.analyze_team_composition(red_picks)
    
    # Get detailed hero information
    api_service = MLBBAPIService()
    
    blue_heroes = []
    for hero_id in blue_picks:
        hero_details = api_service.get_hero_details(hero_id)
        if hero_details:
            blue_heroes.append(hero_details)
    
    red_heroes = []
    for hero_id in red_picks:
        hero_details = api_service.get_hero_details(hero_id)
        if hero_details:
            red_heroes.append(hero_details)
    
    # Calculate matchup predictions (simplified)
    matchup_score = 50  # Neutral
    if blue_analysis['synergy'] > red_analysis['synergy']:
        matchup_score += min((blue_analysis['synergy'] - red_analysis['synergy']) * 2, 20)
    elif red_analysis['synergy'] > blue_analysis['synergy']:
        matchup_score -= min((red_analysis['synergy'] - blue_analysis['synergy']) * 2, 20)
    
    context = {
        'draft': {
            'id': draft.id,
            'name': draft.name,
            'is_completed': draft.is_completed
        },
        'blue_analysis': blue_analysis,
        'red_analysis': red_analysis,
        'blue_heroes': blue_heroes,
        'red_heroes': red_heroes,
        'matchup_prediction': {
            'blue_win_probability': matchup_score,
            'red_win_probability': 100 - matchup_score,
            'confidence': 'Medium'  # Could be calculated based on data quality
        }
    }
    
    return render(request, 'draft/analytics.html', context)

def get_heroes_api(request):
    """API endpoint to get all heroes with current stats"""
    api_service = MLBBAPIService()
    heroes = api_service.get_hero_list()
    
    # Filter and search
    role_filter = request.GET.get('role')
    search_query = request.GET.get('search', '').lower()
    
    if role_filter and role_filter != 'all':
        heroes = [h for h in heroes if h['role'].lower() == role_filter.lower()]
    
    if search_query:
        heroes = [h for h in heroes if search_query in h['name'].lower()]
    
    return JsonResponse({
        'heroes': heroes,
        'total': len(heroes)
    })

def get_hero_details_api(request, hero_id):
    """API endpoint to get detailed hero information"""
    api_service = MLBBAPIService()
    
    # Get comprehensive hero data
    hero_details = api_service.get_hero_details(hero_id)
    hero_counters = api_service.get_hero_counters(hero_id)
    hero_compatibility = api_service.get_hero_compatibility(hero_id)
    
    if not hero_details:
        return JsonResponse({'error': 'Hero not found'}, status=404)
    
    return JsonResponse({
        'hero': hero_details,
        'counters': hero_counters,
        'compatibility': hero_compatibility
    })
