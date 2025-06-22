"use client"

import type React from "react"
import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"

export default function ClientLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const pathname = usePathname()
  const isRootPage = pathname === "/"

  return (
    <>
      {!isRootPage && (
        <header className="bg-white shadow p-4">
          <div className="max-w-7xl mx-auto flex items-center">
            <Link href="/" className="">
              <Image src="/githire-logo.png" alt="GitHired Logo" width={200} height={50} />
            </Link>
          </div>
        </header>
      )}

      {/* Main content */}
      <main>{children}</main>
    </>
  )
}
