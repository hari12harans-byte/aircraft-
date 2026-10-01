from __future__ import annotations
import html

def get_email_template(event_type: str, context: dict, lang: str = 'en') -> dict[str, str]:
    """
    Returns {'subject': '...', 'html': '...', 'text': '...'}
    Multi-lingual responsive HTML emails in English, Tamil, and Hindi.
    """
    lang = (lang or 'en').lower()
    if lang not in ('en', 'ta', 'hi'):
        lang = 'en'

    brand_color = '#0b63ce'
    dark_accent = '#10233d'
    user_name = html.escape(context.get('name') or 'Traveler')
    api_base = context.get('api_base_url', 'http://localhost:8000').rstrip('/')

    titles = {
        'EMAIL_VERIFICATION': {
            'en': 'Verify your email address — YatraFlow',
            'ta': 'உங்கள் மின்னஞ்சலை சரிபார்க்கவும் — YatraFlow',
            'hi': 'अपना ईमेल पता सत्यापित करें — YatraFlow'
        },
        'PASSWORD_RESET': {
            'en': 'Reset your YatraFlow password',
            'ta': 'உங்கள் YatraFlow கடவுச்சொல்லை மீட்டமைக்கவும்',
            'hi': 'अपना YatraFlow पासवर्ड रीसेट करें'
        },
        'WELCOME': {
            'en': 'Welcome to YatraFlow Airport Copilot',
            'ta': 'YatraFlow-விற்கு நல்வரவு',
            'hi': 'YatraFlow में आपका स्वागत है'
        },
        'TRIP_CONFIRMATION': {
            'en': f"Trip Confirmed: {context.get('flight_number', 'Flight')} — YatraFlow",
            'ta': f"பயணம் உறுதிப்படுத்தப்பட்டது: {context.get('flight_number', 'விமானம்')} — YatraFlow",
            'hi': f"यात्रा की पुष्टि: {context.get('flight_number', 'उड़ान')} — YatraFlow"
        },
        'CONNECTION_AT_RISK': {
            'en': f"⚠️ Urgent: Connection At Risk ({context.get('flight_number', 'Flight')})",
            'ta': f"⚠️ அவசரம்: இணைப்பு விமானம் ஆபத்தில் உள்ளது ({context.get('flight_number', 'விமானம்')})",
            'hi': f"⚠️ आवश्यक: कनेक्टिंग उड़ान जोखिम में है ({context.get('flight_number', 'उड़ान')})"
        },
        'GATE_CHANGED': {
            'en': f"✈️ Gate Changed to {context.get('new_gate', 'Gate')} — {context.get('flight_number', 'Flight')}",
            'ta': f"✈️ வாயில் மாற்றப்பட்டது: {context.get('new_gate', 'வாயில்')} — {context.get('flight_number', 'விமானம்')}",
            'hi': f"✈️ गेट बदल गया है: {context.get('new_gate', 'गेट')} — {context.get('flight_number', 'उड़ान')}"
        },
        'FLIGHT_DELAYED': {
            'en': f"Flight Delayed: {context.get('flight_number', 'Flight')} (+{context.get('delay_minutes', '0')} min)",
            'ta': f"விமானம் தாமதம்: {context.get('flight_number', 'விமானம்')} (+{context.get('delay_minutes', '0')} நிமிடம்)",
            'hi': f"उड़ान में विलंब: {context.get('flight_number', 'उड़ान')} (+{context.get('delay_minutes', '0')} मिनट)"
        },
        'BOARDING_REMINDER': {
            'en': f"Boarding Reminder: {context.get('flight_number', 'Flight')} closes in {context.get('minutes_left', '60')}m",
            'ta': f"போர்டிங் நினைவூட்டல்: {context.get('flight_number', 'விமானம்')} {context.get('minutes_left', '60')} நிமிடங்களில் முடிவடைகிறது",
            'hi': f"बोर्डिंग रिमाइंडर: {context.get('flight_number', 'उड़ान')} {context.get('minutes_left', '60')} मिनट में बंद होगी"
        }
    }

    subject = titles.get(event_type, {}).get(lang, titles.get(event_type, {}).get('en', 'YatraFlow Notification'))

    # Message content generator
    content_html = ""
    action_button = ""

    if event_type == 'EMAIL_VERIFICATION':
        verify_url = f"{api_base}/api/auth/verify?token={context.get('token', '')}"
        if lang == 'ta':
            content_html = f"<p>வணக்கம் {user_name},</p><p>YatraFlow-விற்கு நல்வரவு. உங்கள் கணக்கைச் செயல்படுத்த கீழே உள்ள பொத்தானைக் கிளிக் செய்து உங்கள் மின்னஞ்சல் முகவரியைச் சரிபார்க்கவும்:</p>"
            action_button = f'<a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">மின்னஞ்சலைச் சரிபார்க்கவும்</a>'
        elif lang == 'hi':
            content_html = f"<p>नमस्ते {user_name},</p><p>YatraFlow में आपका स्वागत है। अपना खाता सक्रिय करने के लिए कृपया नीचे दिए गए बटन पर क्लिक करके अपना ईमेल सत्यापित करें:</p>"
            action_button = f'<a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">ईमेल सत्यापित करें</a>'
        else:
            content_html = f"<p>Hi {user_name},</p><p>Welcome to YatraFlow. Please verify your email address to activate your account and start receiving live flight and connection intelligence:</p>"
            action_button = f'<a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">Verify Email Address</a>'

    elif event_type == 'PASSWORD_RESET':
        reset_url = f"{api_base}/#reset?token={context.get('token', '')}"
        if lang == 'ta':
            content_html = f"<p>வணக்கம் {user_name},</p><p>உங்கள் YatraFlow கடவுச்சொல்லை மீட்டமைக்க கோரிக்கை பெறப்பட்டது. புதிய கடவுச்சொல்லை அமைக்க கீழே கிளிக் செய்யவும். இந்தக் குறிப்பு 30 நிமிடங்களில் காலாவதியாகும்:</p>"
            action_button = f'<a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">கடவுச்சொல்லை மீட்டமைக்கவும்</a>'
        elif lang == 'hi':
            content_html = f"<p>नमस्ते {user_name},</p><p>आपके YatraFlow पासवर्ड रीसेट करने का अनुरोध प्राप्त हुआ है। नया पासवर्ड सेट करने के लिए नीचे क्लिक करें (30 मिनट में समाप्त):</p>"
            action_button = f'<a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">पासवर्ड रीसेट करें</a>'
        else:
            content_html = f"<p>Hi {user_name},</p><p>We received a request to reset your YatraFlow password. Click the button below to choose a new password. This link expires in 30 minutes:</p>"
            action_button = f'<a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">Reset Password</a>'

    elif event_type == 'CONNECTION_AT_RISK':
        flight_num = html.escape(context.get('flight_number') or 'Flight')
        margin = html.escape(str(context.get('margin_minutes') or '0'))
        gate = html.escape(context.get('outbound_gate') or 'B12')
        if lang == 'ta':
            content_html = f"<div style='padding:16px;background:#fff1f2;border-left:4px solid #e11d48;border-radius:6px;'><h3 style='margin:0 0 8px;color:#9f1239;'>⚠️ இணைப்பு ஆபத்தில் உள்ளது</h3><p style='margin:0;'>விமானம் {flight_num} புறப்பட மீதமுள்ள அவகாசம்: <strong>{margin} நிமிடங்கள்</strong>. உடனே புறப்படும் வாயில் <strong>{gate}</strong>-க்கு செல்லவும்.</p></div>"
        elif lang == 'hi':
            content_html = f"<div style='padding:16px;background:#fff1f2;border-left:4px solid #e11d48;border-radius:6px;'><h3 style='margin:0 0 8px;color:#9f1239;'>⚠️ कनेक्टिंग उड़ान जोखिम में है</h3><p style='margin:0;'>उड़ान {flight_num} के लिए शेष समय केवल <strong>{margin} मिनट</strong> है। कृपया तुरंत गेट <strong>{gate}</strong> की ओर बढ़ें।</p></div>"
        else:
            content_html = f"<div style='padding:16px;background:#fff1f2;border-left:4px solid #e11d48;border-radius:6px;'><h3 style='margin:0 0 8px;color:#9f1239;'>⚠️ Connection At Risk</h3><p style='margin:0;'>Your connection margin for flight <strong>{flight_num}</strong> is currently <strong>{margin} minutes</strong>. Please proceed directly to Gate <strong>{gate}</strong> via recommended route.</p></div>"
        action_button = f'<a href="{api_base}" style="display:inline-block;padding:12px 24px;background:#e11d48;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">Open Rescue Route</a>'

    elif event_type == 'GATE_CHANGED':
        flight_num = html.escape(context.get('flight_number') or 'Flight')
        old_g = html.escape(context.get('old_gate') or '—')
        new_g = html.escape(context.get('new_gate') or '—')
        content_html = f"<div style='padding:16px;background:#eff6ff;border-left:4px solid #2563eb;border-radius:6px;'><h3 style='margin:0 0 8px;color:#1e40af;'>✈️ Gate Changed</h3><p style='margin:0;'>Flight <strong>{flight_num}</strong> gate updated from <strong>{old_g}</strong> to <strong>{new_g}</strong>.</p></div>"
        action_button = f'<a href="{api_base}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">View Gate on Airport Map</a>'

    else:
        desc = html.escape(context.get('message') or 'New operational update available.')
        content_html = f"<p>Hi {user_name},</p><p>{desc}</p>"
        action_button = f'<a href="{api_base}" style="display:inline-block;padding:12px 24px;background:{brand_color};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">Open YatraFlow</a>'

    # Master Email Template
    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:24px 12px;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1e293b;">
  <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:580px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.06);border:1px solid #e2e8f0;">
    <!-- Header -->
    <tr>
      <td style="padding:24px 28px;background:{dark_accent};color:#ffffff;">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
          <tr>
            <td style="font-size:20px;font-weight:900;letter-spacing:-0.5px;">
              <span style="display:inline-block;background:{brand_color};color:#ffffff;padding:4px 8px;border-radius:6px;margin-right:6px;">✈</span> YatraFlow
            </td>
            <td align="right" style="font-size:11px;color:#94a3b8;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">
              Aviation Copilot
            </td>
          </tr>
        </table>
      </td>
    </tr>
    <!-- Main Body -->
    <tr>
      <td style="padding:32px 28px;line-height:1.6;font-size:15px;">
        {content_html}
        {f"<div style='margin-top:24px;'>{action_button}</div>" if action_button else ""}
        <p style="margin-top:28px;font-size:12px;color:#64748b;border-top:1px solid #f1f5f9;padding-top:16px;">
          If you did not make this request or have questions, contact passenger assistance directly inside the app.
        </p>
      </td>
    </tr>
    <!-- Footer -->
    <tr>
      <td style="padding:16px 28px;background:#f8fafc;font-size:11px;color:#94a3b8;text-align:center;border-top:1px solid #e2e8f0;">
        YatraFlow Intelligent Airport Operations · Confidential & Secure
      </td>
    </tr>
  </table>
</body>
</html>"""

    return {
        'subject': subject,
        'html': html_body,
        'text': f"{subject}\n\n{content_html.replace('<p>', '').replace('</p>', '\n')}\n\nOpen YatraFlow: {api_base}"
    }
