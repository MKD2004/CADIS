import { useState } from "react";
import HeroUpload from "@/components/HeroUpload";
import ResultsDashboard from "@/components/ResultsDashboard";
import { processPdf, analyzeSample } from "@/lib/api";
import { useDocument } from "@/context/DocumentContext";

export default function Analyze() {
  const { doc, setDoc } = useDocument();
  const [fileName, setFileName] = useState(doc?.filename || "");
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFile = async (file) => {
    setError(null);
    setIsProcessing(true);
    try {
      const data = await processPdf(file);
      setFileName(file.name);
      setDoc(data);
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.details || err.message || "Processing failed.";
      setError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSample = async (sample) => {
    setError(null);
    setIsProcessing(true);
    try {
      const data = await analyzeSample(sample.document_id);
      setFileName(sample.title || sample.document_id);
      setDoc(data);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || "Failed to analyze sample.";
      setError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setDoc(null);
    setFileName("");
    setError(null);
  };

  if (doc) {
    return <ResultsDashboard data={doc} fileName={fileName} onReset={handleReset} />;
  }

  return (
    <HeroUpload
      onFileAccepted={handleFile}
      onSampleSelect={handleSample}
      error={error}
      isProcessing={isProcessing}
    />
  );
}
