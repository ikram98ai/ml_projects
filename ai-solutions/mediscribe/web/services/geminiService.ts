import { GoogleGenAI, Type, SchemaType } from "@google/genai";
import { SoapNote } from "../types";

// In a real production app, these calls would be proxied through the FastAPI backend 
// to keep the API key secure. For this POC, we call Gemini directly from the client.

const getAiClient = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    throw new Error("API_KEY is missing from environment variables");
  }
  return new GoogleGenAI({ apiKey });
};

// Helper to convert Blob to Base64
const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64String = reader.result as string;
      // Remove data url prefix (e.g., "data:audio/wav;base64,")
      const base64Data = base64String.split(',')[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

export const processConsultationAudio = async (
  audioBlob: Blob
): Promise<{ transcript: string; soapNote: SoapNote }> => {
  const ai = getAiClient();
  const base64Audio = await blobToBase64(audioBlob);

  const model = "gemini-2.5-flash"; // Using Flash for speed/cost efficiency for audio processing

  const prompt = `
    You are an expert medical scribe assisting a doctor. 
    1. Transcribe the audio of this medical consultation verbatim.
    2. Create a structured SOAP note (Subjective, Objective, Assessment, Plan) based on the consultation.
    
    Return the response in JSON format.
  `;

  const response = await ai.models.generateContent({
    model,
    contents: {
      parts: [
        {
          inlineData: {
            mimeType: audioBlob.type || 'audio/wav',
            data: base64Audio,
          },
        },
        { text: prompt },
      ],
    },
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          transcript: { type: Type.STRING, description: "Verbatim transcription of the audio" },
          soapNote: {
            type: Type.OBJECT,
            properties: {
              subjective: { type: Type.STRING, description: "Patient's symptoms and history" },
              objective: { type: Type.STRING, description: "Physical exam findings and vital signs" },
              assessment: { type: Type.STRING, description: "Diagnosis and clinical impression" },
              plan: { type: Type.STRING, description: "Treatment, prescriptions, and follow-up" },
            },
            required: ["subjective", "objective", "assessment", "plan"],
          },
        },
        required: ["transcript", "soapNote"],
      },
    },
  });

  const jsonText = response.text;
  if (!jsonText) throw new Error("No response from AI");
  
  return JSON.parse(jsonText);
};

export const askFollowUpQuestion = async (
  transcript: string,
  history: { role: string; parts: { text: string }[] }[],
  question: string
): Promise<string> => {
  const ai = getAiClient();
  const chat = ai.chats.create({
    model: "gemini-2.5-flash",
    config: {
      systemInstruction: `You are a helpful medical assistant. You have access to the following consultation transcript: "${transcript}". Answer the doctor's questions based strictly on this context.`,
    },
    history: history,
  });

  const result = await chat.sendMessage({ message: question });
  return result.text || "I could not generate a response.";
};
