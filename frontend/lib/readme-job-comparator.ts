import { generateText } from "ai"
import { google } from "@ai-sdk/google"

export interface ReadmeComparison {
  repository: string
  similarityScore: number
  summary: string
  keyMatches: string[]
  relevantSections: string[]
}

export async function compareReadmeToJob(
  readme: string,
  jobDescription: string,
  repositoryName: string
): Promise<ReadmeComparison> {
  try {
    const prompt = `
      Compare this repository README with the job description and provide a detailed analysis.
      
      REPOSITORY: ${repositoryName}
      
      README CONTENT:
      ${readme.substring(0, 3000)} // Limit to avoid token limits
      
      JOB DESCRIPTION:
      ${jobDescription}
      
      Please analyze:
      1. How similar is this project to the job requirements?
      2. What specific technologies/skills mentioned in the job are demonstrated in this project?
      3. What are the key matching points between the project and job?
      4. Which sections of the README are most relevant to the job?
      
      Provide response in JSON format:
      {
        "similarityScore": number (0-100),
        "summary": "Brief summary of how this project relates to the job",
        "keyMatches": ["array", "of", "matching", "technologies/skills"],
        "relevantSections": ["array", "of", "relevant", "readme", "sections"]
      }
    `

    const { text } = await generateText({
      model: google("gemini-1.5-flash"),
      prompt: prompt,
      maxTokens: 1000,
    })

    const analysis = JSON.parse(text)

    return {
      repository: repositoryName,
      similarityScore: analysis.similarityScore || 0,
      summary: analysis.summary || "No analysis available",
      keyMatches: analysis.keyMatches || [],
      relevantSections: analysis.relevantSections || [],
    }
  } catch (error) {
    console.error("Error comparing README to job:", error)

    // Fallback to a default error state
    return {
      repository: repositoryName,
      similarityScore: 0,
      summary: "Failed to analyze README due to an error.",
      keyMatches: [],
      relevantSections: [],
    }
  }
}
