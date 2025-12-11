# LLM Assistant functions using Groq API

import re
import requests
from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL
from database import get_all_detections, get_all_repairs, get_detection_stats
from utils import nearest_neighbor_path

def call_groq_llm(messages, system_prompt=None):
    """Call Groq LLM API"""
    try:
        if not GROQ_API_KEY or GROQ_API_KEY == "your-api-key-here":
            print("Groq API key not configured!")
            return None
            
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROQ_MODEL,
            "messages": all_messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 401:
            print("Groq API: Invalid API key! Please update GROQ_API_KEY in config.py")
            print("Get a valid key from: https://console.groq.com/keys")
            return None
            
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        print("Groq API: Request timed out")
        return None
    except Exception as e:
        print(f"Groq API error: {e}")
        return None

def build_system_prompt(stats, detections, repairs):
    """Build the system prompt with current data context"""
    high_risk_samples = [d for d in detections if d['confidence'] >= 0.8][:5]
    
    return f"""You are an intelligent AI assistant for a Pothole Detection System. You can have natural conversations and help users with any questions about road damage detection and repairs.

## Current System Data:
- Total Active Defects: {stats['total_detections']}
- Potholes: {stats['total_potholes']}
- Cracks: {stats['total_cracks']}
- High Risk (>80% confidence): {stats['high_severity']}
- Medium Risk (50-80%): {stats['medium_severity']}  
- Low Risk (<50%): {stats['low_severity']}
- Already Fixed: {stats['fixed_count']}
- Average Detection Confidence: {stats['avg_confidence']}%

## Sample High Risk Detections:
{chr(10).join([f"- ID {d['id']}: {d['type']} at ({d['lat']:.4f}, {d['lng']:.4f}), Confidence: {d['confidence']*100:.0f}%" for d in high_risk_samples]) if high_risk_samples else "None"}

## Recent Repairs:
{chr(10).join([f"- {r['type']} fixed on {r['repair_date']}" for r in repairs[-5:]]) if repairs else "No repairs yet"}

## Your Capabilities:
1. **Answer ANY question** about the system, road damage, potholes, cracks, etc.
2. **Generate reports** - summarize data, create analysis
3. **Find repair routes** - calculate shortest path to fix issues
4. **Filter by risk** - show high/medium/low risk defects
5. **View specific detections** - show details of specific pothole/crack
6. **Track repairs** - help update and track fixed issues
7. **Provide insights** - analyze patterns, suggest priorities

## Important Instructions:
- Be conversational and helpful, not robotic
- If user asks something unclear, ask for clarification
- If user asks about things outside road damage, politely redirect
- Use markdown formatting for better readability
- When user wants to fix something, guide them through the process
- Be concise but informative
- If asked "how are you" or casual chat, respond naturally then offer help

Remember: You're a smart assistant, not a keyword-matcher. Understand the user's INTENT, not just keywords."""

def detect_intent_and_content(user_message, detections, repairs, stats):
    """Detect user intent and prepare special content for UI display"""
    content = None
    message_lower = user_message.lower()
    
    # Check for specific detection request
    specific_match = re.search(r'(show|view|display|see|find|get)\s*(me\s*)?(pothole|crack|detection|defect|id)\s*#?(\d+)', message_lower)
    if specific_match:
        detection_id = int(specific_match.group(4))
        matching = [d for d in detections if d['id'] == detection_id]
        
        if matching:
            det = matching[0]
            content = {
                'type': 'view_detection',
                'data': {
                    'detection': det,
                    'dashboard_url': f"/dashboard?highlight={det['id']}&lat={det['lat']}&lng={det['lng']}"
                }
            }
    
    # Check for risk level filtering
    elif re.search(r'(show|list|get|find|display|what|which).*(high|critical|urgent|dangerous|severe)\s*(risk|priority|severity)?', message_lower):
        high_risk = [d for d in detections if d['confidence'] >= 0.8]
        content = {
            'type': 'risk_filter',
            'data': {
                'risk_level': 'high',
                'count': len(high_risk),
                'detections': sorted(high_risk, key=lambda x: -x['confidence'])[:30]
            }
        }
    
    elif re.search(r'(show|list|get|find|display|what|which).*(medium|moderate|middle)\s*(risk|priority|severity)?', message_lower):
        medium_risk = [d for d in detections if 0.5 <= d['confidence'] < 0.8]
        content = {
            'type': 'risk_filter',
            'data': {
                'risk_level': 'medium',
                'count': len(medium_risk),
                'detections': sorted(medium_risk, key=lambda x: -x['confidence'])[:30]
            }
        }
    
    elif re.search(r'(show|list|get|find|display|what|which).*(low|minor|small)\s*(risk|priority|severity)?', message_lower):
        low_risk = [d for d in detections if d['confidence'] < 0.5]
        content = {
            'type': 'risk_filter',
            'data': {
                'risk_level': 'low',
                'count': len(low_risk),
                'detections': sorted(low_risk, key=lambda x: -x['confidence'])[:30]
            }
        }
    
    # Check for report request
    elif re.search(r'(report|summary|overview|statistics|stats|total|count|how many)', message_lower):
        content = {'type': 'report', 'data': stats}
    
    # Check for path/route request
    elif re.search(r'(path|route|shortest|direction|navigate|visit|fix\s*today|repair\s*route)', message_lower):
        numbers = re.findall(r'\d+', user_message)
        count = int(numbers[0]) if numbers else 10
        
        priority_detections = sorted(detections, key=lambda x: -x['confidence'])[:count]
        
        if priority_detections:
            path_order, total_dist = nearest_neighbor_path(priority_detections)
            ordered_points = [priority_detections[i] for i in path_order]
            route_polyline = [[p['lat'], p['lng']] for p in ordered_points]
            
            content = {
                'type': 'path',
                'data': {
                    'points': ordered_points,
                    'total_distance': round(total_dist, 2),
                    'estimated_time': f"{int(total_dist / 30 * 60)} mins",
                    'route_polyline': route_polyline
                }
            }
    
    # Check for data extraction request
    elif re.search(r'(list|extract|export|all|data|download|priority\s*list)', message_lower):
        priority_detections = sorted(detections, key=lambda x: -x['confidence'])[:50]
        content = {
            'type': 'data',
            'data': {'detections': priority_detections}
        }
    
    # Check for fix/repair request
    elif re.search(r'(fix|repair|mark|update|complete|done|finished|solved)', message_lower):
        pending = [d for d in detections][:20]
        content = {
            'type': 'fix',
            'data': {
                'pending_detections': pending,
                'recent_repairs': [
                    {
                        'type': r.get('type', ''),
                        'location': f"{r.get('lat', '')}, {r.get('lng', '')}",
                        'date': r.get('repair_date', ''),
                        'technician': r.get('technician', ''),
                        'notes': r.get('notes', '')
                    }
                    for r in repairs[-10:]
                ],
                'stats': stats
            }
        }
    
    return content

def generate_fallback_response(user_message, stats):
    """Generate contextual fallback responses when LLM is unavailable"""
    message_lower = user_message.lower()
    
    # Greeting patterns
    if re.search(r'(hello|hi|hey|good morning|good afternoon|good evening)', message_lower):
        fallback = f"Hello! 👋 I'm your Road Damage Assistant.\n\n"
        fallback += f"**Current System Status:**\n"
        fallback += f"- 🕳️ Active defects: **{stats['total_detections']}**\n"
        fallback += f"- 🔴 High risk: {stats['high_severity']} | 🟡 Medium: {stats['medium_severity']} | 🟢 Low: {stats['low_severity']}\n"
        fallback += f"- ✅ Already fixed: {stats['fixed_count']}\n\n"
        fallback += "**Try asking me:**\n"
        fallback += "• *\"Show high risk detections\"*\n"
        fallback += "• *\"Generate a report\"*\n"
        fallback += "• *\"Plan a repair route for 10 potholes\"*\n"
        fallback += "• *\"I want to fix something\"*"
    
    # How are you patterns
    elif re.search(r'(how are you|how\'s it going|what\'s up)', message_lower):
        fallback = f"I'm doing great, thanks for asking! 😊\n\n"
        fallback += f"I'm currently monitoring **{stats['total_detections']}** road defects.\n"
        fallback += f"There are **{stats['high_severity']}** high-priority issues that need attention!\n\n"
        fallback += "How can I help you today?"
    
    # Help patterns
    elif re.search(r'(help|what can you do|capabilities|features)', message_lower):
        fallback = "🤖 **I can help you with:**\n\n"
        fallback += "📊 **Reports** - Get statistics and summaries\n"
        fallback += "🗺️ **Route Planning** - Find shortest repair paths\n"
        fallback += "⚠️ **Risk Filtering** - View high/medium/low risk detections\n"
        fallback += "🔍 **Search** - Find specific potholes or cracks\n"
        fallback += "🔧 **Track Repairs** - Mark issues as fixed\n\n"
        fallback += "Just ask naturally, like:\n"
        fallback += "• *\"What's the current status?\"*\n"
        fallback += "• *\"Show me critical issues\"*\n"
        fallback += "• *\"Plan a route to fix 5 potholes\"*"
    
    # Thanks patterns
    elif re.search(r'(thank|thanks|appreciate)', message_lower):
        fallback = "You're welcome! 😊\n\nIs there anything else I can help you with?"
    
    # Default fallback
    else:
        fallback = f"I understand you're asking: *\"{user_message}\"*\n\n"
        fallback += f"📊 **Here's the current status:**\n"
        fallback += f"- Total active defects: **{stats['total_detections']}**\n"
        fallback += f"- Potholes: {stats['total_potholes']} | Cracks: {stats['total_cracks']}\n"
        fallback += f"- High risk: 🔴 {stats['high_severity']} | Medium: 🟡 {stats['medium_severity']} | Low: 🟢 {stats['low_severity']}\n"
        fallback += f"- Fixed: ✅ {stats['fixed_count']}\n\n"
        fallback += "**Quick actions you can try:**\n"
        fallback += "• Use the buttons above for common tasks\n"
        fallback += "• Ask *\"show high risk\"* to filter by severity\n"
        fallback += "• Ask *\"fix\"* to update repair status\n\n"
        fallback += "⚠️ *Note: LLM service is currently unavailable. Basic responses only.*"
    
    return fallback

def process_chat_message(user_message, history):
    """Main function to process chat messages"""
    stats = get_detection_stats()
    detections = get_all_detections()
    repairs = get_all_repairs()
    
    # Detect intent and prepare UI content
    content = detect_intent_and_content(user_message, detections, repairs, stats)
    
    # Build system prompt with current data
    system_prompt = build_system_prompt(stats, detections, repairs)
    
    # Prepare messages for LLM
    messages = [{"role": m['role'], "content": m['content']} for m in history[-10:]]
    messages.append({"role": "user", "content": user_message})
    
    # Call LLM
    llm_response = call_groq_llm(messages, system_prompt)
    
    if llm_response:
        return {
            'success': True,
            'response': llm_response,
            'content': content
        }
    else:
        # Generate fallback response
        fallback = generate_fallback_response(user_message, stats)
        return {
            'success': True,
            'response': fallback,
            'content': content
        }
