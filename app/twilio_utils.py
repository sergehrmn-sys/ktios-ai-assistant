import os
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Gather

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    if not TWILIO_AUTH_TOKEN:
        return False
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    return validator.validate(url, params, signature)

def twiml_gather_speech(prompt: str, action_url: str) -> str:
    vr = VoiceResponse()
    vr.say(prompt, language="fr-CA", voice="Polly.Celine")
    g = Gather(input="speech", action=action_url, method="POST", speech_timeout="auto", language="fr-CA", enhanced=True, timeout=6)
    g.say("Je vous écoute.", language="fr-CA", voice="Polly.Celine")
    vr.append(g)
    vr.say("Je n'ai rien entendu. Répétez s'il vous plaît.", language="fr-CA", voice="Polly.Celine")
    vr.redirect("/webhooks/twilio/voice", method="POST")
    return str(vr)

def twiml_say_and_gather(reply: str, action_url: str) -> str:
    vr = VoiceResponse()
    vr.say(reply, language="fr-CA", voice="Polly.Celine")
    g = Gather(input="speech", action=action_url, method="POST", speech_timeout="auto", language="fr-CA", enhanced=True, timeout=6)
    g.say("Je vous écoute.", language="fr-CA", voice="Polly.Celine")
    vr.append(g)
    vr.say("Je n'ai rien entendu. Répétez s'il vous plaît.", language="fr-CA", voice="Polly.Celine")
    vr.redirect("/webhooks/twilio/voice", method="POST")
    return str(vr)