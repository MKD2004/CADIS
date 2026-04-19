require('dotenv').config();
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 5000;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://127.0.0.1:8000';

// Middleware
app.use(cors());
app.use(express.json());

// Setup Multer to catch PDF uploads temporarily
const upload = multer({ dest: 'uploads/' });

app.get('/api/status', (req, res) => {
    res.json({ status: 'Gateway Online', ml_backend: FASTAPI_URL });
});

// The main processing route
// The main processing route & orchestrator
// The main processing route & orchestrator
app.post('/api/process-pdf', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No PDF file uploaded.' });
        }

        console.log(`[Gateway] Received PDF: ${req.file.originalname}`);

        // --- STEP 1: INGESTION (ChromaDB) ---
        console.log(`[Gateway] 1/4: Extracting text and embedding into ChromaDB...`);
        const formData = new FormData();
        formData.append('file', fs.createReadStream(req.file.path), req.file.originalname);
        formData.append('extract_images', 'false'); // Set to false since VLM is disabled
        formData.append('run_vlm', 'false');

        const ingestRes = await axios.post(`${FASTAPI_URL}/api/v1/process-pdf`, formData, {
            headers: { ...formData.getHeaders() },
            timeout: 120000 
        });

        const docData = ingestRes.data;
        const textToAnalyze = docData.enriched_text || docData.extracted_text || docData.text || "";

        // --- STEP 2: NER EXTRACTION (GliNER) ---
        console.log(`[Gateway] 2/4: Running Zero-Shot NER...`);
        let groupedEntities = {};
        let totalEntities = 0;

        try {
            const nerRes = await axios.post(`${FASTAPI_URL}/api/v1/ner/extract`, {
                text: textToAnalyze.substring(0, 2500), 
                entity_labels: ["Threat Actor", "Malware", "IP Address", "Vulnerability", "Company", "Person", "Location", "Date", "Money"],
                threshold: 0.4,
                flat_ner: true
            });

            const rawEntities = nerRes.data.entities || [];
            rawEntities.forEach(ent => {
                const label = ent.label.toUpperCase();
                if (!groupedEntities[label]) groupedEntities[label] = [];
                groupedEntities[label].push(ent);
                totalEntities++;
            });
        } catch (err) {
            console.error('[Gateway] NER Extraction failed:', err.message);
        }

        // --- STEP 3: DISTILBART SUMMARIZATION ---
        console.log(`[Gateway] 3/4: Generating Executive Summary...`);
        let finalSummary = textToAnalyze; // Fallback is raw text
        try {
            const sumRes = await axios.post(`${FASTAPI_URL}/api/v1/summary/generate`, {
                text: textToAnalyze
            });
            if (sumRes.data && sumRes.data.executive_summary) {
                finalSummary = sumRes.data.executive_summary;
            }
        } catch (err) {
            console.error('[Gateway] Summarization failed:', err.message);
        }

        // --- STEP 4: AMBIGUITY DETECTION ---
        console.log(`[Gateway] 4/4: Scanning for Ambiguities...`);
        const ambiguityKeywords = ["unclear", "ambiguity", "unknown", "inconclusive", "cannot determine", "suspected"];
        let ambiguitiesCount = 0;
        ambiguityKeywords.forEach(keyword => {
            const regex = new RegExp(keyword, "gi");
            const matches = textToAnalyze.match(regex);
            if (matches) ambiguitiesCount += matches.length;
        });

        // Clean up the temp file
        fs.unlinkSync(req.file.path);

       // --- STEP 5: ASSEMBLE THE BENTO BOX PAYLOAD ---
        console.log(`[Gateway] Success! Sending assembled payload to React.`);
        
        const finalPayload = {
            ...docData,
            executive_summary: finalSummary,   
            document_entities: groupedEntities,
            
            // React specifically renders the UI from this object
            pipeline_flags: {
                ...(docData.pipeline_flags || {}),
                ambiguities_found: ambiguitiesCount
            }
        };


        // 🛑 --- THE PAYLOAD INTERCEPTOR --- 🛑
        console.log("\n================ PAYLOAD SANITY CHECK ================");
        console.log("1. Summary Length:", finalPayload.executive_summary ? finalPayload.executive_summary.length + " characters" : "UNDEFINED");
        console.log("2. Summary Preview:", finalPayload.executive_summary ? `"${finalPayload.executive_summary.substring(0, 75)}..."` : "N/A");
        console.log("3. Ambiguities Count:", finalPayload.pipeline_flags?.ambiguities_found ?? "UNDEFINED");
        console.log("4. Root JSON Keys:", Object.keys(finalPayload).join(", "));
        console.log("======================================================\n");

        res.json(finalPayload);

    } catch (error) {
        console.error('[Gateway Error]', error.message);
        if (req.file) fs.unlinkSync(req.file.path); 
        res.status(500).json({ error: 'Failed to process document', details: error.message });
    }
});

// ── RAG Chat Interface Route ──────────────────────────────────
app.post('/api/chat', async (req, res) => {
    try {
        const { query, document_id } = req.body;
        
        if (!query) {
            return res.status(400).json({ error: 'Query is required.' });
        }

        console.log(`[Gateway] Routing chat query to Brain: "${query}"`);

        // Forward the user's question to FastAPI (ChromaDB + RoBERTa)
        const pyRes = await axios.post(`${FASTAPI_URL}/api/v1/search/query`, {
            query: query,
            top_k: 3,
            document_id: document_id === "current" ? null : document_id
        }, {
            timeout: 30000
        });

        // Simply pass RoBERTa's exact answer straight to the UI! 
        // No more "Vector Space Match" hardcoding.
        res.json({ 
            answer: pyRes.data.answer || "I could not find a definitive answer in the document." 
        });

    } catch (error) {
        console.error('[Gateway Chat Error]', error.message);
        res.status(500).json({ error: 'Failed to query the neural backend.' });
    }
});

app.listen(PORT, () => {
    console.log(`API Gateway running on http://localhost:${PORT}`);
    console.log(`Proxying ML requests to ${FASTAPI_URL}`);
});