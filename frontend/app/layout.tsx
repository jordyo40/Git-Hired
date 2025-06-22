import type React from "react"
import type { Metadata } from "next"
import "../styles/globals.css"
import ClientLayout from "./ClientLayout"

export const metadata: Metadata = {
  title: "GitHired",
  description: "Find your dream tech job.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  )
}
