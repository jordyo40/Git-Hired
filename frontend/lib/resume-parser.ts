export interface ParsedResume {
  name: string
  email: string
  githubUrl: string
  text: string
  filename: string
}

export async function parseResumes(files: File[]): Promise<ParsedResume[]> {
  const results: ParsedResume[] = []

  for (const file of files) {
    try {
      let text = ""

      if (file.type === "application/pdf") {
        // For demo purposes, we'll simulate PDF parsing
        // In a real implementation, you'd use a library like pdf-parse
        text = await simulatePDFParsing(file)
      } else if (file.type.includes("text") || file.name.endsWith(".txt")) {
        text = await file.text()
      } else {
        // For other formats (DOC, DOCX), you'd need appropriate parsers
        text = await simulateDocParsing(file)
      }

      const parsed = extractResumeData(text, file.name)
      if (parsed) {
        results.push(parsed)
      }
    } catch (error) {
      console.error(`Error parsing ${file.name}:`, error)
    }
  }

  return results
}

async function simulatePDFParsing(file: File): Promise<string> {
  // Simulate PDF parsing - in reality, you'd use pdf-parse or similar
  return `
    John Doe
    Email: john.doe@example.com
    Phone: (555) 123-4567
    GitHub: https://github.com/johndoe
    
    EXPERIENCE
    Senior Software Engineer at TechCorp (2020-2023)
    - Developed React applications with TypeScript
    - Built REST APIs using Node.js and Express
    - Implemented CI/CD pipelines with GitHub Actions
    
    SKILLS
    JavaScript, TypeScript, React, Node.js, Python, AWS, Docker   
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of Technology (2016-2020)
  `
}

async function simulateDocParsing(file: File): Promise<string> {
  // Simulate DOC/DOCX parsing - in reality, you'd use mammoth.js or similar
  return `
    Jane Smith
    jane.smith@email.com
    GitHub: https://github.com/janesmith
    
    PROFESSIONAL SUMMARY
    Full-stack developer with 5 years of experience in web development
    
    TECHNICAL SKILLS
    - Frontend: React, Vue.js, Angular, HTML5, CSS3
    - Backend: Node.js, Python, Java, PHP
    - Databases: MongoDB, PostgreSQL, MySQL
    - Cloud: AWS, Azure, Google Cloud Platform
    
    WORK EXPERIENCE
    Full Stack Developer - WebSolutions Inc. (2021-Present)
    - Built responsive web applications using React and Node.js
    - Designed and implemented RESTful APIs
    - Collaborated with cross-functional teams using Agile methodologies
  `
}

function extractResumeData(text: string, filename: string): ParsedResume | null {
  // Extract name (first line that looks like a name)
  const nameMatch = text.match(/^([A-Z][a-z]+ [A-Z][a-z]+)/m)
  const name = nameMatch ? nameMatch[1] : filename.replace(/\.[^/.]+$/, "")

  // Extract email
  const emailMatch = text.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i)
  const email = emailMatch ? emailMatch[1] : ""

  // Extract GitHub URL
  const githubMatch = text.match(/(https?:\/\/github\.com\/[^\s)]+)/i)
  const githubUrl = githubMatch ? githubMatch[1] : ""

  if (!githubUrl) {
    console.warn(`No GitHub URL found in ${filename}`)
  }

  return {
    name,
    email,
    githubUrl,
    text,
    filename,
  }
}
