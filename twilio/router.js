// Twilio Function (servicio `forward-call`, path /router, visibilidad Protected).
// Capa de enrutamiento delante del agente: la plataforma de notificaciones va al
// celular (Function forward-call); todas las demás llamadas van a ElevenLabs.
//
// Variables de entorno del servicio:
//   NOTIF_FROM      números que se desvían al celular, separados por coma (E.164)
//   FORWARD_URL     URL de la Function forward-call del mismo servicio
//   ELEVENLABS_URL  https://api.us.elevenlabs.io/twilio/inbound_call
exports.handler = function (context, event, callback) {
  const twiml = new Twilio.twiml.VoiceResponse();
  const notificadores = (context.NOTIF_FROM || '').split(',').map(s => s.trim());

  if (notificadores.includes(event.From)) {
    twiml.redirect({ method: 'POST' }, context.FORWARD_URL);
  } else {
    twiml.redirect({ method: 'POST' }, context.ELEVENLABS_URL);
  }
  return callback(null, twiml);
};
