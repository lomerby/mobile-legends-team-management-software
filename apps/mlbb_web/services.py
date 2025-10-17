import requests
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class MLBBAPIService:
    """Enhanced service for integrating MLBB API data with the draft system"""
    
    def __init__(self):
        self.base_url = settings.PROD_URL
        self.cache_timeout = 300  # 5 minutes cache
        
    def _get_cached_data(self, cache_key: str, api_url: str) -> Optional[Dict]:
        """Get data from cache or API with caching"""
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data:
                    cache.set(cache_key, data, self.cache_timeout)
                    return data
        except Exception as e:
            logger.error(f"Error fetching data from {api_url}: {str(e)}")
            
        return None
    
    def get_hero_list(self) -> List[Dict]:
        """Get comprehensive hero list with current stats"""
        cache_key = 'mlbb_hero_list_enhanced'
        api_url = f'{self.base_url}hero-list-new/'
        
        data = self._get_cached_data(cache_key, api_url)
        if not data or 'data' not in data:
            return []
            
        heroes = []
        for record in data['data']['records']:
            hero_data = record.get('data', {})
            hero = hero_data.get('hero', {})
            
            if hero:
                heroes.append({
                    'id': hero.get('heroid'),
                    'name': hero.get('heroname'),
                    'role': hero.get('role', 'Unknown'),
                    'lane': hero.get('lane', 'Unknown'),
                    'image_url': hero.get('heroimage', ''),
                    'win_rate': record.get('data', {}).get('main_hero_win_rate', 0) * 100,
                    'pick_rate': record.get('data', {}).get('main_hero_appearance_rate', 0) * 100,
                    'ban_rate': record.get('data', {}).get('main_hero_ban_rate', 0) * 100,
                })
                
        return sorted(heroes, key=lambda x: x['name'])
    
    def get_hero_counters(self, hero_id: int) -> Dict[str, List[Dict]]:
        """Get hero counter relationships"""
        cache_key = f'mlbb_hero_counter_{hero_id}'
        api_url = f'{self.base_url}hero-counter/{hero_id}/'
        
        data = self._get_cached_data(cache_key, api_url)
        if not data or 'data' not in data or not data['data']['records']:
            return {'strong_against': [], 'weak_against': []}
            
        record = data['data']['records'][0]['data']
        
        return {
            'strong_against': self._process_counter_data(record.get('sub_hero', [])),
            'weak_against': self._process_counter_data(record.get('sub_hero_last', []))
        }
    
    def get_hero_compatibility(self, hero_id: int) -> Dict[str, List[Dict]]:
        """Get hero compatibility/synergy data"""
        cache_key = f'mlbb_hero_compatibility_{hero_id}'
        api_url = f'{self.base_url}hero-compatibility/{hero_id}/'
        
        data = self._get_cached_data(cache_key, api_url)
        if not data or 'data' not in data or not data['data']['records']:
            return {'synergizes_with': []}
            
        record = data['data']['records'][0]['data']
        
        return {
            'synergizes_with': self._process_counter_data(record.get('sub_hero', []))
        }
    
    def get_hero_details(self, hero_id: int) -> Optional[Dict]:
        """Get detailed hero information"""
        cache_key = f'mlbb_hero_detail_{hero_id}'
        api_url = f'{self.base_url}hero-detail/{hero_id}/'
        
        data = self._get_cached_data(cache_key, api_url)
        if not data or 'data' not in data or not data['data']['records']:
            return None
            
        hero_data = data['data']['records'][0]['data']['hero']['data']
        
        return {
            'id': hero_data.get('heroid'),
            'name': hero_data.get('heroname'),
            'role': hero_data.get('role'),
            'lane': hero_data.get('lane'),
            'image_url': hero_data.get('heroimage', ''),
            'skills': hero_data.get('heroskilllist', []),
            'difficulty': hero_data.get('herodifficulty', 1),
            'attributes': hero_data.get('heroattribute', {}),
        }
    
    def get_hero_rankings(self, days: int = 1, rank: str = 'all', size: int = 20) -> List[Dict]:
        """Get current hero rankings and meta"""
        cache_key = f'mlbb_hero_rank_{days}_{rank}_{size}'
        api_url = f'{self.base_url}hero-rank/?days={days}&rank={rank}&size={size}&sort_field=win_rate&sort_order=desc'
        
        data = self._get_cached_data(cache_key, api_url)
        if not data or 'data' not in data or not data['data']['records']:
            return []
            
        rankings = []
        for record in data['data']['records']:
            hero_data = record.get('data', {})
            
            rankings.append({
                'id': hero_data.get('main_heroid'),
                'name': hero_data.get('main_heroname'),
                'win_rate': hero_data.get('main_hero_win_rate', 0) * 100,
                'pick_rate': hero_data.get('main_hero_appearance_rate', 0) * 100,
                'ban_rate': hero_data.get('main_hero_ban_rate', 0) * 100,
                'rank': record.get('rank', 0),
                'tier': self._calculate_tier(hero_data.get('main_hero_win_rate', 0)),
            })
            
        return rankings
    
    def get_hero_positions(self, role: str = 'all', lane: str = 'all') -> List[Dict]:
        """Get heroes by position/role"""
        cache_key = f'mlbb_hero_position_{role}_{lane}'
        api_url = f'{self.base_url}hero-position/?role={role}&lane={lane}&size=50'
        
        data = self._get_cached_data(cache_key, api_url)
        if not data or 'data' not in data or not data['data']['records']:
            return []
            
        heroes = []
        for record in data['data']['records']:
            hero_data = record.get('data', {})
            hero = hero_data.get('hero', {})
            
            if hero:
                heroes.append({
                    'id': hero.get('heroid'),
                    'name': hero.get('heroname'),
                    'role': hero.get('role'),
                    'lane': hero.get('lane'),
                    'image_url': hero.get('heroimage', ''),
                    'relations': hero_data.get('relation', {}),
                })
                
        return heroes
    
    def _process_counter_data(self, counter_list: List[Dict]) -> List[Dict]:
        """Process counter/compatibility data"""
        processed = []
        for counter in counter_list:
            processed.append({
                'hero_id': counter.get('sub_heroid'),
                'hero_name': counter.get('sub_heroname'),
                'win_rate_change': counter.get('increase_win_rate', 0),
                'effectiveness': self._calculate_effectiveness(counter.get('increase_win_rate', 0))
            })
        return processed
    
    def _calculate_tier(self, win_rate: float) -> str:
        """Calculate hero tier based on win rate"""
        win_rate_percent = win_rate * 100 if win_rate < 1 else win_rate
        
        if win_rate_percent >= 55:
            return 'S+'
        elif win_rate_percent >= 53:
            return 'S'
        elif win_rate_percent >= 51:
            return 'A'
        elif win_rate_percent >= 49:
            return 'B'
        elif win_rate_percent >= 47:
            return 'C'
        else:
            return 'D'
    
    def _calculate_effectiveness(self, win_rate_change: float) -> str:
        """Calculate counter effectiveness"""
        if win_rate_change >= 5:
            return 'Strong'
        elif win_rate_change >= 2:
            return 'Moderate'
        elif win_rate_change >= -2:
            return 'Neutral'
        elif win_rate_change >= -5:
            return 'Weak'
        else:
            return 'Very Weak'

class DraftRecommendationService:
    """Service for providing draft recommendations"""
    
    def __init__(self):
        self.api_service = MLBBAPIService()
    
    def get_pick_recommendations(self, 
                               current_picks: List[int], 
                               current_bans: List[int], 
                               enemy_picks: List[int],
                               phase: str = 'pick') -> List[Dict]:
        """Get hero recommendations for current draft state"""
        
        all_heroes = self.api_service.get_hero_list()
        available_heroes = [h for h in all_heroes 
                          if h['id'] not in current_picks + current_bans + enemy_picks]
        
        recommendations = []
        
        for hero in available_heroes:
            score = self._calculate_draft_score(
                hero['id'], 
                current_picks, 
                enemy_picks, 
                phase
            )
            
            hero_rec = hero.copy()
            hero_rec['draft_score'] = score
            hero_rec['recommendation_reason'] = self._get_recommendation_reason(
                hero['id'], current_picks, enemy_picks, score
            )
            
            recommendations.append(hero_rec)
        
        # Sort by draft score (highest first)
        recommendations.sort(key=lambda x: x['draft_score'], reverse=True)
        
        return recommendations[:10]  # Top 10 recommendations
    
    def get_ban_recommendations(self, 
                              enemy_picks: List[int], 
                              current_bans: List[int]) -> List[Dict]:
        """Get ban recommendations based on enemy team and meta"""
        
        # Get high priority heroes from current meta
        top_heroes = self.api_service.get_hero_rankings(size=30)
        available_bans = [h for h in top_heroes 
                         if h['id'] not in current_bans + enemy_picks]
        
        recommendations = []
        
        for hero in available_bans:
            # Ban score based on pick rate, win rate, and synergy with enemy
            ban_score = (
                hero['pick_rate'] * 0.4 +  # High pick rate = worth banning
                hero['win_rate'] * 0.3 +   # High win rate = strong hero
                hero['ban_rate'] * 0.3     # Already commonly banned
            )
            
            # Boost score if hero synergizes with enemy team
            for enemy_id in enemy_picks:
                compatibility = self.api_service.get_hero_compatibility(enemy_id)
                for synergy in compatibility['synergizes_with']:
                    if synergy['hero_id'] == hero['id']:
                        ban_score += synergy['win_rate_change'] * 2
            
            hero_rec = hero.copy()
            hero_rec['ban_score'] = ban_score
            hero_rec['ban_reason'] = self._get_ban_reason(hero, enemy_picks)
            
            recommendations.append(hero_rec)
        
        recommendations.sort(key=lambda x: x['ban_score'], reverse=True)
        return recommendations[:8]  # Top 8 ban recommendations
    
    def analyze_team_composition(self, team_picks: List[int]) -> Dict:
        """Analyze team composition and provide insights"""
        if not team_picks:
            return {'roles': {}, 'synergy': 0, 'weaknesses': [], 'strengths': []}
        
        roles = {'Tank': 0, 'Fighter': 0, 'Assassin': 0, 'Mage': 0, 'Marksman': 0, 'Support': 0}
        team_synergy = 0
        
        # Analyze role distribution
        for hero_id in team_picks:
            hero_details = self.api_service.get_hero_details(hero_id)
            if hero_details and hero_details['role']:
                role = hero_details['role']
                if role in roles:
                    roles[role] += 1
        
        # Calculate team synergy (simplified)
        for i, hero1_id in enumerate(team_picks):
            for hero2_id in team_picks[i+1:]:
                compatibility = self.api_service.get_hero_compatibility(hero1_id)
                for synergy in compatibility['synergizes_with']:
                    if synergy['hero_id'] == hero2_id:
                        team_synergy += synergy['win_rate_change']
        
        # Determine strengths and weaknesses
        strengths = []
        weaknesses = []
        
        if roles['Tank'] >= 1:
            strengths.append("Good tankiness and initiation")
        else:
            weaknesses.append("Lacks tankiness and initiation")
        
        if roles['Marksman'] >= 1:
            strengths.append("Strong late-game damage")
        else:
            weaknesses.append("May lack sustained damage")
        
        if sum(roles.values()) == len(team_picks):
            strengths.append("Balanced role distribution")
        
        return {
            'roles': roles,
            'synergy': team_synergy,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'overall_rating': self._calculate_team_rating(roles, team_synergy)
        }
    
    def _calculate_draft_score(self, hero_id: int, ally_picks: List[int], 
                             enemy_picks: List[int], phase: str) -> float:
        """Calculate overall draft score for a hero"""
        score = 50.0  # Base score
        
        # Get hero rankings for base meta score
        rankings = self.api_service.get_hero_rankings(size=50)
        hero_rank = next((h for h in rankings if h['id'] == hero_id), None)
        
        if hero_rank:
            # Base meta strength (0-25 points)
            score += (hero_rank['win_rate'] - 50) * 0.5
            score += min(hero_rank['pick_rate'] * 0.1, 5)
        
        # Synergy with allies (0-15 points)
        for ally_id in ally_picks:
            compatibility = self.api_service.get_hero_compatibility(ally_id)
            for synergy in compatibility['synergizes_with']:
                if synergy['hero_id'] == hero_id:
                    score += min(synergy['win_rate_change'] * 0.5, 3)
        
        # Counter potential against enemies (0-20 points)
        for enemy_id in enemy_picks:
            counters = self.api_service.get_hero_counters(hero_id)
            for counter in counters['strong_against']:
                if counter['hero_id'] == enemy_id:
                    score += min(counter['win_rate_change'] * 0.3, 5)
        
        # Penalty if easily countered by enemies (-10 to 0 points)
        for enemy_id in enemy_picks:
            enemy_counters = self.api_service.get_hero_counters(enemy_id)
            for counter in enemy_counters['strong_against']:
                if counter['hero_id'] == hero_id:
                    score -= min(abs(counter['win_rate_change']) * 0.2, 3)
        
        return max(0, min(100, score))  # Clamp between 0-100
    
    def _get_recommendation_reason(self, hero_id: int, ally_picks: List[int], 
                                 enemy_picks: List[int], score: float) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        if score >= 80:
            reasons.append("Excellent meta pick")
        elif score >= 65:
            reasons.append("Strong meta choice")
        elif score >= 50:
            reasons.append("Solid pick")
        
        # Check for specific synergies or counters
        for ally_id in ally_picks:
            compatibility = self.api_service.get_hero_compatibility(ally_id)
            for synergy in compatibility['synergizes_with']:
                if synergy['hero_id'] == hero_id and synergy['win_rate_change'] > 3:
                    reasons.append(f"Great synergy with {synergy['hero_name']}")
                    break
        
        for enemy_id in enemy_picks:
            counters = self.api_service.get_hero_counters(hero_id)
            for counter in counters['strong_against']:
                if counter['hero_id'] == enemy_id and counter['win_rate_change'] > 3:
                    reasons.append(f"Counters {counter['hero_name']}")
                    break
        
        return " | ".join(reasons) if reasons else "Standard pick"
    
    def _get_ban_reason(self, hero: Dict, enemy_picks: List[int]) -> str:
        """Generate ban recommendation reason"""
        reasons = []
        
        if hero['ban_rate'] > 20:
            reasons.append("Commonly banned")
        if hero['win_rate'] > 55:
            reasons.append("High win rate")
        if hero['pick_rate'] > 15:
            reasons.append("Popular pick")
        
        return " | ".join(reasons) if reasons else "Strategic ban"
    
    def _calculate_team_rating(self, roles: Dict, synergy: float) -> str:
        """Calculate overall team composition rating"""
        role_balance = 1 - abs(5 - sum(roles.values())) * 0.1
        synergy_factor = min(synergy / 10, 1)
        
        overall = (role_balance + synergy_factor) / 2
        
        if overall >= 0.8:
            return "Excellent"
        elif overall >= 0.6:
            return "Good"
        elif overall >= 0.4:
            return "Average"
        elif overall >= 0.2:
            return "Poor"
        else:
            return "Needs Work"