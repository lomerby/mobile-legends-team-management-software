from django.db import models
from django.contrib.auth.models import User
import json

class DraftSession(models.Model):
    """Main draft session model"""
    DRAFT_PHASES = [
        ('ban1', 'Ban Phase 1'),
        ('pick1', 'Pick Phase 1'), 
        ('ban2', 'Ban Phase 2'),
        ('pick2', 'Pick Phase 2'),
        ('ban3', 'Ban Phase 3'),
        ('pick3', 'Pick Phase 3'),
        ('completed', 'Draft Completed'),
    ]
    
    name = models.CharField(max_length=100, default="New Draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_phase = models.CharField(max_length=20, choices=DRAFT_PHASES, default='ban1')
    current_turn = models.CharField(max_length=10, default='blue')  # 'blue' or 'red'
    is_completed = models.BooleanField(default=False)
    session_key = models.CharField(max_length=50, null=True, blank=True)  # For anonymous users
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Draft order tracking
    turn_order = models.JSONField(default=list)  # Stores the turn sequence
    current_turn_index = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_current_phase_display()}"

class Team(models.Model):
    """Team model for blue/red side"""
    TEAM_SIDES = [
        ('blue', 'Blue Side'),
        ('red', 'Red Side'),
    ]
    
    draft_session = models.ForeignKey(DraftSession, on_delete=models.CASCADE, related_name='teams')
    side = models.CharField(max_length=10, choices=TEAM_SIDES)
    name = models.CharField(max_length=50, default="Team")
    
    class Meta:
        unique_together = ['draft_session', 'side']
    
    def __str__(self):
        return f"{self.draft_session.name} - {self.get_side_display()}"

class HeroPick(models.Model):
    """Hero picks for each team"""
    POSITIONS = [
        (1, 'Exp Lane'),
        (2, 'Jungler'), 
        (3, 'Mid Lane'),
        (4, 'Gold Lane'),
        (5, 'Roamer'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='picks')
    hero_id = models.IntegerField()
    hero_name = models.CharField(max_length=50)
    position = models.IntegerField(choices=POSITIONS, null=True, blank=True)
    pick_order = models.IntegerField()  # Order in which hero was picked
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['pick_order']
        unique_together = ['team', 'pick_order']
    
    def __str__(self):
        return f"{self.team.side} - {self.hero_name} (Pick {self.pick_order})"

class HeroBan(models.Model):
    """Hero bans for each team"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='bans')
    hero_id = models.IntegerField()
    hero_name = models.CharField(max_length=50)
    ban_order = models.IntegerField()  # Order in which hero was banned
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ban_order']
        unique_together = ['team', 'ban_order']
    
    def __str__(self):
        return f"{self.team.side} - {self.hero_name} (Ban {self.ban_order})"

class DraftTemplate(models.Model):
    """Saved draft templates for reuse"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=50, null=True, blank=True)
    
    # Template data stored as JSON
    blue_picks = models.JSONField(default=list)  # [{"hero_id": 1, "hero_name": "Miya", "position": 4}, ...]
    red_picks = models.JSONField(default=list)
    blue_bans = models.JSONField(default=list)   # [{"hero_id": 2, "hero_name": "Balmond"}, ...]
    red_bans = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)  # Allow sharing
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class DraftNote(models.Model):
    """Notes and strategy comments for drafts"""
    draft_session = models.ForeignKey(DraftSession, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
