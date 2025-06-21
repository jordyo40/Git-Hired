import mammoth from "mammoth"
import * as pdfjsLib from "pdfjs-dist"

// Set up the worker source for pdfjs-dist
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`

export interface ParsedResume {
  name: string
  email: string
  github_username: string
  text: string
  filename: string
  links: string[]
  fileContent: ArrayBuffer
  fileType: string
}

export async function parseResumes(files: File[]): Promise<ParsedResume[]> {
  const results: ParsedResume[] = []

  for (const file of files) {
    try {
      let text = ""
      const arrayBuffer = await file.arrayBuffer()

      if (file.type === "application/pdf") {
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer.slice(0) }).promise
        let content = ""
        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i)
          const textContent = await page.getTextContent()
          content += textContent.items.map((item: any) => item.str).join(" ")
        }
        text = content
      } else if (file.type.includes("text") || file.name.endsWith(".txt")) {
        // Use TextDecoder to handle ArrayBuffer -> string
        text = new TextDecoder().decode(arrayBuffer)
      } else if (
        file.name.endsWith(".docx") ||
        file.type ===
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ) {
        const result = await mammoth.extractRawText({
          arrayBuffer: arrayBuffer.slice(0),
        })
        text = result.value
      } else {
        console.warn(
          `Unsupported file type: ${file.name} (${file.type}), skipping`,
        )
        continue
      }

      const parsed = extractResumeData(text, file.name)
      if (parsed) {
        results.push({
          ...parsed,
          fileContent: arrayBuffer,
          fileType: file.type,
        })
      }
    } catch (error) {
      console.error(`Error parsing ${file.name}:`, error)
    }
  }

  return results
}

function extractResumeData(
  text: string,
  filename: string,
): Omit<ParsedResume, "fileContent" | "fileType"> | null {
  // Extract name (first line that looks like a name)
  const nameMatch = text.match(/^([A-Z][a-z]+ [A-Z][a-z]+)/m)
  const name = nameMatch ? nameMatch[1] : filename.replace(/\.[^/.]+$/, "")
  console.log(`NAME: ${name}`)

  // Extract email
  const emailMatch = text.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i)
  const email = emailMatch ? emailMatch[1] : ""
  console.log(`EMAIL: ${email}`)

  // Extract GitHub URL
  const m = text.match(/github\.com\/([\w.-]+)/i);
  const github_username = m ? m[1] : "";
  console.log("GITHUB USERNAME:", github_username);

  const links = getAllLinks(text);
  console.log("LINKS:", links);

  if (!github_username) {
    console.warn(`No GitHub Username found in ${filename}`)
  }

  return {
    name,
    email,
    github_username,
    text,
    filename,
    links,
  }
}

function getAllLinks(text: string) {
  // This regex is designed to match a wide variety of URLs, including those with or without a protocol.
  const urlPattern =
    /\b((?:[a-z][\w-]+:(?:\/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,24}\/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»""'']))/gi
  return [...text.matchAll(urlPattern)].map((m) => m[0])
}