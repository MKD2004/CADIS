const rateLimit = require('express-rate-limit');

function limitHandler(windowMinutes) {
  return (_req, res) => {
    const retryAfter = res.getHeader('Retry-After');
    res.status(429).json({
      error: 'rate_limit_exceeded',
      message: `Too many requests. Please wait ${windowMinutes} minutes before trying again.`,
      retryAfter: Number(retryAfter),
    });
  };
}

const strictLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  handler: limitHandler(15),
});

const uploadLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  handler: limitHandler(60),
});

const generalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  handler: limitHandler(15),
});

module.exports = { strictLimiter, uploadLimiter, generalLimiter };
