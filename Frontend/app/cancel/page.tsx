"use client"

import { Header } from "@/components/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { XCircle, ArrowLeft, CreditCard } from "lucide-react"
import Link from "next/link"

export default function CancelPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <div className="container py-8 max-w-2xl mx-auto">
        <Card className="text-center">
          <CardHeader className="pb-4">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900">
              <XCircle className="h-10 w-10 text-orange-600 dark:text-orange-400" />
            </div>
            <CardTitle className="text-2xl">Subscription Cancelled</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <p className="text-muted-foreground">
                Your subscription process was cancelled. No charges have been made to your account.
              </p>
            </div>

            <div className="bg-muted/50 rounded-lg p-4">
              <h3 className="font-semibold mb-2">What you're missing out on:</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>• Advanced team analytics and insights</p>
                <p>• Complete historical data access</p>
                <p>• Custom league tracking capabilities</p>
                <p>• Data export features for analysis</p>
                <p>• Priority customer support</p>
              </div>
            </div>

            <div className="space-y-3">
              <Link href="/subscription">
                <Button className="w-full">
                  <CreditCard className="h-4 w-4 mr-2" />
                  Try Again - Subscribe Now
                </Button>
              </Link>
              
              <Link href="/">
                <Button variant="outline" className="w-full">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Continue with Free Version
                </Button>
              </Link>
            </div>

            <div className="text-sm text-muted-foreground">
              <p>Have questions about our premium features?</p>
              <p>Feel free to contact us for more information.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 