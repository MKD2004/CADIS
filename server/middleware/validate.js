const path = require('path');

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

function validatePdfUpload(req, res, next) {
  if (!req.file) {
    return res.status(400).json({
      error: 'invalid_file',
      message: 'No file was uploaded.',
    });
  }

  const { originalname, mimetype, size } = req.file;

  if (!originalname || originalname.trim() === '') {
    return res.status(400).json({
      error: 'invalid_file',
      message: 'Filename must not be empty.',
    });
  }

  const ext = path.extname(originalname).toLowerCase();
  if (mimetype !== 'application/pdf' || ext !== '.pdf') {
    return res.status(400).json({
      error: 'invalid_file',
      message: 'Only PDF files under 10MB are accepted.',
    });
  }

  if (size > MAX_FILE_SIZE) {
    return res.status(400).json({
      error: 'invalid_file',
      message: `Only PDF files under 10MB are accepted. Received ${(size / 1024 / 1024).toFixed(1)}MB.`,
    });
  }

  next();
}

function validateChatQuery(req, res, next) {
  const { query, document_id } = req.body;

  if (!query || typeof query !== 'string' || query.trim() === '') {
    return res.status(400).json({
      error: 'invalid_query',
      message: 'Query must be between 1 and 500 characters.',
    });
  }

  if (query.trim().length > 500) {
    return res.status(400).json({
      error: 'invalid_query',
      message: 'Query must be between 1 and 500 characters.',
    });
  }

  if (document_id !== undefined && document_id !== null) {
    if (typeof document_id !== 'string' || document_id.trim() === '') {
      return res.status(400).json({
        error: 'invalid_query',
        message: 'document_id must be a non-empty string.',
      });
    }
  }

  req.body.query = query.trim();
  next();
}

module.exports = { validatePdfUpload, validateChatQuery };
