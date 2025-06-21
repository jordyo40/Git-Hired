"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Github, Star, GitCommit, AlertTriangle, CheckCircle, XCircle } from "lucide-react"
import type { JobPosting, Candidate } from "@/app/page"

interface ResultsDialogProps {
  job: JobPosting
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ResultsDialog({ job, open, onOpenChange }: ResultsDialogProps) {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null)

  useEffect(() => {
    if (open) {
      const allCandidates = JSON.parse(localStorage.getItem("candidates") || "[]")
      const jobCandidates: Candidate[] = allCandidates.filter((c: Candidate) => c.jobId === job.id)
      setCandidates(jobCandidates.sort((a: Candidate, b: Candidate) => b.score - a.score))
      if (jobCandidates.length > 0) {
        setSelectedCandidate(jobCandidates[0])
      }
    }
  }, [open, job.id])

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600"
    if (score >= 60) return "text-yellow-600"
    return "text-red-600"
  }

  const getScoreBadgeVariant = (score: number) => {
    if (score >= 80) return "default"
    if (score >= 60) return "secondary"
    return "destructive"
  }

  const getCodeQualityIcon = (score: number) => {
    if (score >= 80) return <CheckCircle className="w-4 h-4 text-green-600" />
    if (score >= 60) return <AlertTriangle className="w-4 h-4 text-yellow-600" />
    return <XCircle className="w-4 h-4 text-red-600" />
  }

  const formatUrl = (url: string) => {
    if (url.startsWith("http://") || url.startsWith("https://")) {
      return url
    }
    return `//${url}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Analysis Results - {job.name}</DialogTitle>
        </DialogHeader>

        <div className="flex gap-6 h-[calc(90vh-120px)]">
          {/* Candidates List */}
          <div className="w-1/3 border-r pr-6">
            <h3 className="font-semibold mb-4">Candidates ({candidates.length})</h3>
            <ScrollArea className="h-full">
              <div className="space-y-3">
                {candidates.map((candidate) => (
                  <Card
                    key={candidate.id}
                    className={`cursor-pointer transition-colors ${
                      selectedCandidate?.id === candidate.id ? "ring-2 ring-blue-500" : ""
                    }`}
                    onClick={() => setSelectedCandidate(candidate)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Avatar className="w-8 h-8">
                            <AvatarFallback>{candidate.name.charAt(0)}</AvatarFallback>
                          </Avatar>
                          <div>
                            <CardTitle className="text-sm">{candidate.name}</CardTitle>
                            <CardDescription className="text-xs">{candidate.email}</CardDescription>
                          </div>
                        </div>
                        <Badge variant={getScoreBadgeVariant(candidate.score)}>{candidate.score}/100</Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                        <Github className="w-3 h-3" />
                        <span className="truncate">{candidate.github_username}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                        {getCodeQualityIcon(candidate.githubAnalysis.codeQualityScore || 0)}
                        <span>Code Quality: {candidate.githubAnalysis.codeQualityScore || 0}/100</span>
                      </div>
                      <Progress value={candidate.score} className="h-1" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* Candidate Details */}
          {selectedCandidate && (
            <div className="flex-1 overflow-y-auto">
              <Tabs defaultValue="overview" className="h-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="resume">Resume</TabsTrigger>
                  <TabsTrigger value="github">GitHub Analysis</TabsTrigger>
                  <TabsTrigger value="comparison">Job Comparison</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Avatar>
                          <AvatarFallback>{selectedCandidate.name.charAt(0)}</AvatarFallback>
                        </Avatar>
                        {selectedCandidate.name}
                        <Badge variant={getScoreBadgeVariant(selectedCandidate.score)} className="ml-auto">
                          Overall Score: {selectedCandidate.score}/100
                        </Badge>
                      </CardTitle>
                      <CardDescription>{selectedCandidate.email}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-medium mb-2">GitHub Profile</h4>
                          <a
                            href={`https://github.com/${selectedCandidate.github_username}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline flex items-center gap-1"
                          >
                            <Github className="w-4 h-4" />
                            View Profile
                          </a>
                        </div>
                        <div>
                          <h4 className="font-medium mb-2">Profile Stats</h4>
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span>Total Repositories:</span>
                              <span>{selectedCandidate.githubAnalysis.repositories.length}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Total Stars:</span>
                              <span>{selectedCandidate.githubAnalysis.totalStars}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Lines of Code:</span>
                              <span>{selectedCandidate.githubAnalysis.totalLinesOfCode || 0}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Detailed Score Breakdown</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Technical Proficiency (40%)</span>
                            <span className="text-sm">{selectedCandidate.githubAnalysis.technicalScore || 0}/100</span>
                          </div>
                          <Progress value={selectedCandidate.githubAnalysis.technicalScore || 0} />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Job Relevance (35%)</span>
                            <span className="text-sm">{selectedCandidate.githubAnalysis.relevanceScore}/100</span>
                          </div>
                          <Progress value={selectedCandidate.githubAnalysis.relevanceScore} />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Code Quality (15%)</span>
                            <span className="text-sm">
                              {selectedCandidate.githubAnalysis.codeQualityScore || 0}/100
                            </span>
                          </div>
                          <Progress value={selectedCandidate.githubAnalysis.codeQualityScore || 0} />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm">Activity & Growth (10%)</span>
                            <span className="text-sm">{selectedCandidate.githubAnalysis.activityScore || 0}/100</span>
                          </div>
                          <Progress value={selectedCandidate.githubAnalysis.activityScore || 0} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="resume" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Resume Content</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ScrollArea className="h-96">
                        <div className="whitespace-pre-wrap text-sm leading-relaxed">
                          {selectedCandidate.resumeText}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Extracted Links</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {selectedCandidate.extractedLinks?.map((link, index) => (
                          <div key={index} className="flex items-center gap-2">
                            <Badge variant="outline">{link.type}</Badge>
                            <a
                              href={formatUrl(link.url)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline text-sm"
                            >
                              {link.url}
                            </a>
                          </div>
                        )) || <p className="text-gray-500 text-sm">No additional links found</p>}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="github" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Programming Languages & Proficiency</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(selectedCandidate.githubAnalysis.languageProficiency || {})
                          .sort(([, a], [, b]) => (b as any).score - (a as any).score)
                          .slice(0, 8)
                          .map(([language, data]) => {
                            const proficiency = data as any
                            return (
                              <div key={language} className="space-y-1">
                                <div className="flex justify-between items-center">
                                  <span className="text-sm font-medium">{language}</span>
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="text-xs">
                                      {proficiency.linesOfCode} lines
                                    </Badge>
                                    <span className="text-sm">{proficiency.score}/100</span>
                                  </div>
                                </div>
                                <Progress value={proficiency.score} />
                                <div className="text-xs text-gray-600">
                                  Used in {proficiency.repositories} repositories
                                </div>
                              </div>
                            )
                          })}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Repository Analysis</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ScrollArea className="h-96">
                        <div className="space-y-4">
                          {selectedCandidate.githubAnalysis.repositories
                            .sort((a, b) => (b.codeQualityScore || 0) - (a.codeQualityScore || 0))
                            .map((repo) => (
                              <div key={repo.name} className="border rounded-lg p-4">
                                <div className="flex justify-between items-start mb-3">
                                  <div>
                                    <h4 className="font-medium">{repo.name}</h4>
                                    <p className="text-sm text-gray-600 mt-1">{repo.description}</p>
                                  </div>
                                  <div className="flex flex-col gap-1">
                                    <Badge variant="outline">Relevance: {repo.relevanceScore}/100</Badge>
                                    <Badge variant="outline">Code Quality: {repo.codeQualityScore || 0}/100</Badge>
                                  </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4 mb-3">
                                  <div>
                                    <h5 className="text-sm font-medium mb-1">Technologies Used</h5>
                                    <div className="flex flex-wrap gap-1">
                                      {repo.technologies?.map((tech) => (
                                        <Badge key={tech} variant="secondary" className="text-xs">
                                          {tech}
                                        </Badge>
                                      )) || (
                                        <Badge variant="secondary" className="text-xs">
                                          {repo.language}
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                  <div>
                                    <h5 className="text-sm font-medium mb-1">Code Metrics</h5>
                                    <div className="text-xs text-gray-600 space-y-1">
                                      <div>Lines of Code: {repo.linesOfCode || "N/A"}</div>
                                      <div>Files: {repo.fileCount || "N/A"}</div>
                                      <div>Complexity Score: {repo.complexityScore || "N/A"}/100</div>
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-4 text-xs text-gray-500">
                                  <div className="flex items-center gap-1">
                                    <Star className="w-3 h-3" />
                                    {repo.stars}
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <GitCommit className="w-3 h-3" />
                                    {repo.commits} commits
                                  </div>
                                  <div className="flex items-center gap-1">
                                    {getCodeQualityIcon(repo.codeQualityScore || 0)}
                                    Quality Score
                                  </div>
                                </div>

                                {repo.codeIssues && repo.codeIssues.length > 0 && (
                                  <div className="mt-3 p-2 bg-red-50 rounded border-l-4 border-red-400">
                                    <h6 className="text-sm font-medium text-red-800 mb-1">Code Issues Found</h6>
                                    <ul className="text-xs text-red-700 space-y-1">
                                      {repo.codeIssues.slice(0, 3).map((issue, index) => (
                                        <li key={index}>• {issue}</li>
                                      ))}
                                      {repo.codeIssues.length > 3 && (
                                        <li>• +{repo.codeIssues.length - 3} more issues</li>
                                      )}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ))}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="comparison" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Skills Match Analysis</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex flex-wrap gap-2">
                          {job.requiredSkills.map((skill) => {
                            const isMatched = selectedCandidate.githubAnalysis.skillsMatch.includes(skill)
                            const proficiency = selectedCandidate.githubAnalysis.skillProficiency?.[skill] || 0
                            return (
                              <div key={skill} className="flex items-center gap-2">
                                <Badge
                                  variant={isMatched ? "default" : "outline"}
                                  className={isMatched ? "bg-green-100 text-green-800" : ""}
                                >
                                  {skill} {isMatched && "✓"}
                                </Badge>
                                {isMatched && <span className="text-xs text-gray-600">({proficiency}/100)</span>}
                              </div>
                            )
                          })}
                        </div>
                        <div className="mt-4">
                          <p className="text-sm text-gray-600">
                            Matched {selectedCandidate.githubAnalysis.skillsMatch.length} out of{" "}
                            {job.requiredSkills.length} required skills
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>README vs Job Description Similarity</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {selectedCandidate.githubAnalysis.readmeComparison?.map((comparison, index) => (
                          <div key={index} className="border rounded-lg p-3">
                            <div className="flex justify-between items-center mb-2">
                              <h5 className="font-medium">{comparison.repository}</h5>
                              <Badge variant="outline">Similarity: {comparison.similarityScore}%</Badge>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">{comparison.summary}</p>
                            <div className="text-xs text-gray-500">
                              <strong>Key Matches:</strong> {comparison.keyMatches.join(", ")}
                            </div>
                          </div>
                        )) || <p className="text-gray-500 text-sm">No README comparison data available</p>}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Comprehensive Grading Criteria</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <h4 className="font-medium text-sm">Technical Proficiency (40%)</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                              <li>• Code complexity and architecture (15%)</li>
                              <li>• Language expertise and best practices (10%)</li>
                              <li>• Documentation and comments (8%)</li>
                              <li>• Error handling and security (7%)</li>
                            </ul>
                          </div>
                          <div className="space-y-2">
                            <h4 className="font-medium text-sm">Job Relevance (35%)</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                              <li>• Project similarity to job requirements (15%)</li>
                              <li>• Required skills demonstration (10%)</li>
                              <li>• Industry-relevant experience (5%)</li>
                              <li>• Technology stack alignment (5%)</li>
                            </ul>
                          </div>
                          <div className="space-y-2">
                            <h4 className="font-medium text-sm">Code Quality (15%)</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                              <li>• Code readability and structure (6%)</li>
                              <li>• Testing and CI/CD practices (4%)</li>
                              <li>• Security vulnerabilities (-20 points)</li>
                              <li>• Performance optimizations (5%)</li>
                            </ul>
                          </div>
                          <div className="space-y-2">
                            <h4 className="font-medium text-sm">Activity & Growth (10%)</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                              <li>• Recent activity and contributions (4%)</li>
                              <li>• Learning new technologies (3%)</li>
                              <li>• Open source contributions (2%)</li>
                              <li>• Profile completeness (1%)</li>
                            </ul>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
