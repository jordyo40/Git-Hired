import type { RepositoryCode, CodeFile } from "./github-analyzer"

export interface CodeQualityAnalysis {
  overallScore: number
  complexityScore: number
  readabilityScore: number
  securityScore: number
  documentationScore: number
  testingScore: number
  issues: string[]
  strengths: string[]
}

export async function analyzeCodeQuality(repoCode: RepositoryCode): Promise<CodeQualityAnalysis> {
  const analysis: CodeQualityAnalysis = {
    overallScore: 0,
    complexityScore: 0,
    readabilityScore: 0,
    securityScore: 100, // Start with perfect security score, deduct for issues
    documentationScore: 0,
    testingScore: 0,
    issues: [],
    strengths: [],
  }

  if (repoCode.files.length === 0) {
    return analysis
  }

  // Analyze each file
  for (const file of repoCode.files) {
    analyzeFile(file, analysis)
  }

  // Calculate overall scores
  analysis.complexityScore = calculateComplexityScore(repoCode)
  analysis.readabilityScore = calculateReadabilityScore(repoCode)
  analysis.documentationScore = calculateDocumentationScore(repoCode)
  analysis.testingScore = calculateTestingScore(repoCode)

  // Calculate overall score
  analysis.overallScore = Math.round(
    analysis.complexityScore * 0.25 +
      analysis.readabilityScore * 0.25 +
      analysis.securityScore * 0.25 +
      analysis.documentationScore * 0.15 +
      analysis.testingScore * 0.1,
  )

  return analysis
}

function analyzeFile(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content
  const lines = content.split("\n")

  // Security analysis
  checkSecurityIssues(file, analysis)

  // Code structure analysis
  checkCodeStructure(file, analysis)

  // Documentation analysis
  checkDocumentation(file, analysis)

  // Best practices analysis
  checkBestPractices(file, analysis)
}

function checkSecurityIssues(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content.toLowerCase()
  const securityPatterns = [
    // API Keys and secrets
    { pattern: /api[_-]?key\s*[:=]\s*['"][^'"]+['"]/gi, issue: "Hardcoded API key found", severity: 20 },
    { pattern: /secret[_-]?key\s*[:=]\s*['"][^'"]+['"]/gi, issue: "Hardcoded secret key found", severity: 20 },
    { pattern: /password\s*[:=]\s*['"][^'"]+['"]/gi, issue: "Hardcoded password found", severity: 25 },
    { pattern: /token\s*[:=]\s*['"][^'"]+['"]/gi, issue: "Hardcoded token found", severity: 15 },

    // Database credentials
    { pattern: /mongodb:\/\/[^:]+:[^@]+@/gi, issue: "Database credentials in connection string", severity: 20 },
    { pattern: /mysql:\/\/[^:]+:[^@]+@/gi, issue: "Database credentials in connection string", severity: 20 },

    // Unsafe practices
    { pattern: /eval\s*\(/gi, issue: "Use of eval() function (security risk)", severity: 15 },
    { pattern: /innerHTML\s*=/gi, issue: "Use of innerHTML (XSS risk)", severity: 10 },
    { pattern: /document\.write\s*\(/gi, issue: "Use of document.write (XSS risk)", severity: 10 },

    // SQL Injection risks
    { pattern: /query\s*\+\s*['"`]/gi, issue: "Potential SQL injection vulnerability", severity: 15 },
    { pattern: /execute\s*\(\s*['"`][^'"]*\+/gi, issue: "Potential SQL injection vulnerability", severity: 15 },
  ]

  securityPatterns.forEach(({ pattern, issue, severity }) => {
    if (pattern.test(content)) {
      analysis.issues.push(`${file.path}: ${issue}`)
      analysis.securityScore = Math.max(0, analysis.securityScore - severity)
    }
  })
}

function checkCodeStructure(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const lines = file.content.split("\n")
  const nonEmptyLines = lines.filter((line) => line.trim().length > 0)

  // Check for very long functions
  let currentFunctionLength = 0
  let inFunction = false

  lines.forEach((line, index) => {
    const trimmed = line.trim()

    // Detect function start (simplified)
    if (trimmed.includes("function ") || trimmed.includes("def ") || trimmed.includes("=> {")) {
      inFunction = true
      currentFunctionLength = 0
    }

    if (inFunction) {
      currentFunctionLength++

      // Check for function end (simplified)
      if (trimmed === "}" || (file.language === "Python" && line.match(/^[a-zA-Z]/))) {
        if (currentFunctionLength > 50) {
          analysis.issues.push(`${file.path}:${index + 1}: Function is too long (${currentFunctionLength} lines)`)
        }
        inFunction = false
      }
    }

    // Check line length
    if (line.length > 120) {
      analysis.issues.push(`${file.path}:${index + 1}: Line too long (${line.length} characters)`)
    }
  })

  // Check for code duplication (simplified)
  const duplicateThreshold = 5
  const lineGroups: { [key: string]: number[] } = {}

  nonEmptyLines.forEach((line, index) => {
    const normalized = line.trim().replace(/\s+/g, " ")
    if (normalized.length > 20) {
      // Only check substantial lines
      if (!lineGroups[normalized]) {
        lineGroups[normalized] = []
      }
      lineGroups[normalized].push(index)
    }
  })

  Object.entries(lineGroups).forEach(([line, indices]) => {
    if (indices.length >= duplicateThreshold) {
      analysis.issues.push(`${file.path}: Potential code duplication detected (${indices.length} similar lines)`)
    }
  })
}

function checkDocumentation(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content
  const lines = content.split("\n")
  const codeLines = lines.filter(
    (line) => line.trim().length > 0 && !line.trim().startsWith("//") && !line.trim().startsWith("#"),
  )
  const commentLines = lines.filter((line) => {
    const trimmed = line.trim()
    return trimmed.startsWith("//") || trimmed.startsWith("#") || trimmed.startsWith("/*") || trimmed.startsWith("*")
  })

  const commentRatio = commentLines.length / Math.max(1, codeLines.length)

  if (commentRatio > 0.2) {
    analysis.strengths.push(`${file.path}: Well documented code (${Math.round(commentRatio * 100)}% comments)`)
  } else if (commentRatio < 0.05) {
    analysis.issues.push(`${file.path}: Insufficient documentation (${Math.round(commentRatio * 100)}% comments)`)
  }

  // Check for function documentation
  const functionDocPattern = /(?:\/\*\*[\s\S]*?\*\/|#.*|\/\/.*)\s*(?:function|def|class)/gi
  const functions = content.match(/(?:function|def|class)\s+\w+/gi) || []
  const documentedFunctions = content.match(functionDocPattern) || []

  if (functions.length > 0) {
    const docRatio = documentedFunctions.length / functions.length
    if (docRatio < 0.5) {
      analysis.issues.push(`${file.path}: Functions lack documentation (${Math.round(docRatio * 100)}% documented)`)
    }
  }
}

function checkBestPractices(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content

  // Language-specific best practices
  switch (file.language) {
    case "JavaScript":
    case "TypeScript":
      checkJavaScriptBestPractices(file, analysis)
      break
    case "Python":
      checkPythonBestPractices(file, analysis)
      break
    case "Java":
      checkJavaBestPractices(file, analysis)
      break
  }

  // General best practices
  checkGeneralBestPractices(file, analysis)
}

function checkJavaScriptBestPractices(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content

  // Check for modern JavaScript practices
  if (content.includes("const ") || content.includes("let ")) {
    analysis.strengths.push(`${file.path}: Uses modern JavaScript (const/let)`)
  }

  if (content.includes("var ") && !content.includes("const ") && !content.includes("let ")) {
    analysis.issues.push(`${file.path}: Uses outdated 'var' declarations`)
  }

  // Check for arrow functions
  if (content.includes("=>")) {
    analysis.strengths.push(`${file.path}: Uses modern arrow functions`)
  }

  // Check for async/await
  if (content.includes("async ") && content.includes("await ")) {
    analysis.strengths.push(`${file.path}: Uses modern async/await`)
  }

  // Check for console.log in production code
  if (content.includes("console.log") && !file.path.includes("test")) {
    analysis.issues.push(`${file.path}: Contains console.log statements`)
  }
}

function checkPythonBestPractices(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content
  const lines = content.split("\n")

  // Check for PEP 8 compliance (simplified)
  lines.forEach((line, index) => {
    if (line.includes("\t")) {
      analysis.issues.push(`${file.path}:${index + 1}: Uses tabs instead of spaces (PEP 8)`)
    }
  })

  // Check for type hints
  if (content.includes(": ") && content.includes("->")) {
    analysis.strengths.push(`${file.path}: Uses type hints`)
  }

  // Check for docstrings
  if (content.includes('"""') || content.includes("'''")) {
    analysis.strengths.push(`${file.path}: Contains docstrings`)
  }
}

function checkJavaBestPractices(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content

  // Check for proper exception handling
  if (content.includes("try {") && content.includes("catch")) {
    analysis.strengths.push(`${file.path}: Implements exception handling`)
  }

  // Check for proper access modifiers
  if (content.includes("private ") || content.includes("protected ")) {
    analysis.strengths.push(`${file.path}: Uses proper encapsulation`)
  }
}

function checkGeneralBestPractices(file: CodeFile, analysis: CodeQualityAnalysis): void {
  const content = file.content

  // Check for TODO/FIXME comments
  const todoCount = (content.match(/TODO|FIXME|HACK/gi) || []).length
  if (todoCount > 0) {
    analysis.issues.push(`${file.path}: Contains ${todoCount} TODO/FIXME comments`)
  }

  // Check for error handling
  if (content.includes("try") || content.includes("catch") || content.includes("except")) {
    analysis.strengths.push(`${file.path}: Implements error handling`)
  }
}

function calculateComplexityScore(repoCode: RepositoryCode): number {
  let totalComplexity = 0
  let fileCount = 0

  repoCode.files.forEach((file) => {
    const complexity = calculateFileComplexity(file)
    totalComplexity += complexity
    fileCount++
  })

  const avgComplexity = fileCount > 0 ? totalComplexity / fileCount : 0

  // Convert to score (lower complexity = higher score)
  return Math.max(0, Math.min(100, 100 - avgComplexity * 2))
}

function calculateFileComplexity(file: CodeFile): number {
  const content = file.content
  let complexity = 1 // Base complexity

  // Count decision points
  const decisionPatterns = [
    /if\s*\(/gi,
    /else\s+if\s*\(/gi,
    /while\s*\(/gi,
    /for\s*\(/gi,
    /switch\s*\(/gi,
    /case\s+/gi,
    /catch\s*\(/gi,
    /\?\s*:/gi, // Ternary operator
  ]

  decisionPatterns.forEach((pattern) => {
    const matches = content.match(pattern) || []
    complexity += matches.length
  })

  return complexity
}

function calculateReadabilityScore(repoCode: RepositoryCode): number {
  let totalScore = 0
  let fileCount = 0

  repoCode.files.forEach((file) => {
    const score = calculateFileReadability(file)
    totalScore += score
    fileCount++
  })

  return fileCount > 0 ? Math.round(totalScore / fileCount) : 0
}

function calculateFileReadability(file: CodeFile): number {
  const lines = file.content.split("\n")
  const nonEmptyLines = lines.filter((line) => line.trim().length > 0)

  let score = 100

  // Penalize very long lines
  const longLines = lines.filter((line) => line.length > 120).length
  score -= (longLines / nonEmptyLines.length) * 20

  // Reward consistent indentation
  const indentationPattern = /^(\s*)/
  const indentations = lines
    .map((line) => {
      const match = line.match(indentationPattern)
      return match ? match[1].length : 0
    })
    .filter((indent) => indent > 0)

  if (indentations.length > 0) {
    const avgIndent = indentations.reduce((sum, indent) => sum + indent, 0) / indentations.length
    if (avgIndent >= 2 && avgIndent <= 4) {
      score += 10 // Reward good indentation
    }
  }

  // Reward meaningful variable names
  const variablePattern = /(?:var|let|const|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)/g
  const variables = []
  let match
  while ((match = variablePattern.exec(file.content)) !== null) {
    variables.push(match[1])
  }

  const meaningfulVars = variables.filter(
    (name) => name.length > 2 && !["i", "j", "k", "x", "y", "z"].includes(name.toLowerCase()),
  ).length

  if (variables.length > 0) {
    const meaningfulRatio = meaningfulVars / variables.length
    score += meaningfulRatio * 15
  }

  return Math.max(0, Math.min(100, Math.round(score)))
}

function calculateDocumentationScore(repoCode: RepositoryCode): number {
  let totalScore = 0
  let fileCount = 0

  repoCode.files.forEach((file) => {
    const score = calculateFileDocumentation(file)
    totalScore += score
    fileCount++
  })

  return fileCount > 0 ? Math.round(totalScore / fileCount) : 0
}

function calculateFileDocumentation(file: CodeFile): number {
  const lines = file.content.split("\n")
  const codeLines = lines.filter((line) => {
    const trimmed = line.trim()
    return trimmed.length > 0 && !trimmed.startsWith("//") && !trimmed.startsWith("#") && !trimmed.startsWith("/*")
  })

  const commentLines = lines.filter((line) => {
    const trimmed = line.trim()
    return trimmed.startsWith("//") || trimmed.startsWith("#") || trimmed.startsWith("/*") || trimmed.startsWith("*")
  })

  if (codeLines.length === 0) return 0

  const commentRatio = commentLines.length / codeLines.length
  return Math.min(100, Math.round(commentRatio * 200)) // Scale to 0-100
}

function calculateTestingScore(repoCode: RepositoryCode): number {
  const testFiles = repoCode.files.filter(
    (file) => file.path.includes("test") || file.path.includes("spec") || file.path.includes("__tests__"),
  )

  if (testFiles.length === 0) return 0

  const testRatio = testFiles.length / repoCode.files.length
  let score = Math.min(100, testRatio * 300) // Scale to 0-100

  // Bonus for test frameworks
  testFiles.forEach((file) => {
    const content = file.content.toLowerCase()
    if (
      content.includes("jest") ||
      content.includes("mocha") ||
      content.includes("pytest") ||
      content.includes("junit")
    ) {
      score += 10
    }
  })

  return Math.min(100, Math.round(score))
}
