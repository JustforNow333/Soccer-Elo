"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Header } from "@/components/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle, Crown, ArrowRight } from "lucide-react"
import Link from "next/link"

export default function SuccessPage() {
  const searchParams = useSearchParams()
  const sessionId = searchParams.get("session_id")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // You could verify the session with Stripe here if needed
    const timer = setTimeout(() => {
      setLoading(false)
    }, 1000)

    return () => clearTimeout(timer)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Confirming your subscription...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <div className="container py-8 max-w-2xl mx-auto">
        <Card className="text-center">
          <CardHeader className="pb-4">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
              <CheckCircle className="h-10 w-10 text-green-600 dark:text-green-400" />
            </div>
            <CardTitle className="text-2xl">Subscription Successful!</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <p className="text-muted-foreground">
                Thank you for subscribing to Soccer Elo Premium! Your subscription is now active.
              </p>
              {sessionId && (
                <p className="text-sm text-muted-foreground">
                  Session ID: {sessionId}
                </p>
              )}
            </div>

            <div className="bg-muted/50 rounded-lg p-4">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Crown className="h-5 w-5 text-primary" />
                <span className="font-semibold">Premium Features Unlocked</span>
              </div>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>✓ Advanced team analytics</p>
                <p>✓ Historical data access</p>
                <p>✓ Custom league tracking</p>
                <p>✓ Export data features</p>
                <p>✓ Priority support</p>
              </div>
            </div>

            <div className="space-y-3">
              <Link href="/">
                <Button className="w-full">
                  <ArrowRight className="h-4 w-4 mr-2" />
                  Start Exploring Premium Features
                </Button>
              </Link>
              
              <p className="text-sm text-muted-foreground">
                You'll receive a confirmation email shortly with your subscription details.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 