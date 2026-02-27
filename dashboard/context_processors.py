# context_processors.py
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.auth import get_user_model
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

def dashboard_context(request):
    """Provide dashboard data with fallbacks"""
    if not request.user.is_staff:
        return {}
    
    context = {
        'studio_installed': False,
        'total_users': 0,
        'active_sessions': 0,
        'new_orders': 0,
        'revenue': '0',
        'recent_activities': [],
    }
    
    try:
        # Last 7 days
        last_week = timezone.now() - timedelta(days=7)
        
        # Recent activities from LogEntry
        recent_logs = LogEntry.objects.select_related(
            'user', 'content_type'
        ).order_by('-action_time')[:10]
        
        activities = []
        action_map = {
            ADDITION: {'name': 'Added', 'color': '', 'icon': 'M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z'},
            CHANGE: {'name': 'Changed', 'color': '', 'icon': 'M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z'},
            DELETION: {'name': 'Deleted', 'color': '', 'icon': 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16'},
        }
        
        for log in recent_logs:
            action_info = action_map.get(log.action_flag, {
                'name': 'Unknown',
                'color': 'gray',
                'icon': 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
            })
            
            user_name = log.user.get_full_name() if log.user and log.user.get_full_name() else (log.user.username if log.user else 'System')
            
            activities.append({
                'description': f"{user_name} {action_info['name'].lower()} {log.object_repr}",
                'time': log.action_time.strftime('%Y-%m-%d %H:%M'),
                'status': action_info['name'],
                'color': action_info['color'],
                'icon': action_info['icon'],
            })
        
        # Stats with error handling
        try:
            context['total_users'] = User.objects.count()
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            context['total_users'] = 0
        
        try:
            context['active_sessions'] = User.objects.filter(last_login__gte=last_week).count()
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")
            context['active_sessions'] = 0
        
        # Example calculations (replace with your actual data)
        context['new_orders'] = context['total_users'] // 10  # Example
        context['revenue'] = '{:,.0f}'.format(context['total_users'] * 10)  # Example
        context['recent_activities'] = activities
        
    except Exception as e:
        logger.error(f"Error in dashboard context: {e}")
    
    return context