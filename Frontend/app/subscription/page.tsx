"use client"

import { useState } from "react"
import { loadStripe } from "@stripe/stripe-js"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/hooks/use-toast"
import { CreditCard, Crown, Check, AlertCircle } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

// Initialize Stripe with your publishable key
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "pk_test_51RfDycFQ0X76CRQWJT0cqNejHelfjrbBmaKpukedAOGEbuTr30xJz0HjxavpDHObLdk3H3d7qMQcm0KKHeskwmb9004SgWXXbO")

export default function SubscriptionPage() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email || !email.includes("@")) {
      toast({
        title: "Error",
        description: "Please enter a valid email address",
        variant: "destructive",
      })
      return
    }

    setLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"
      const response = await fetch(`${apiUrl}/create-checkout-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to create checkout session")
      }

      if (data.url) {
        // Redirect to Stripe Checkout
        window.location.href = data.url
      } else {
        throw new Error("No checkout URL received")
      }
    } catch (error) {
      console.error("Subscription error:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start subscription process",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <div className="container py-8 max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <Crown className="h-12 w-12 text-primary mx-auto mb-4" />
          <h1 className="text-4xl font-bold mb-2">Premium Subscription</h1>
          <p className="text-muted-foreground text-lg">
            Unlock advanced features and get the most out of Soccer Elo Rankings
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-2">
          {/* Pricing Card */}
          <Card className="relative">
            <div className="absolute top-4 right-4">
              <Crown className="h-6 w-6 text-primary" />
            </div>
            <CardHeader>
              <CardTitle className="text-2xl">Premium Plan</CardTitle>
              <div className="text-3xl font-bold">
                $9.99
                <span className="text-lg font-normal text-muted-foreground">/month</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>Advanced team analytics</span>
                </div>
                <div className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>Historical data access</span>
                </div>
                <div className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>Custom league tracking</span>
                </div>
                <div className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>Export data features</span>
                </div>
                <div className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>Priority support</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Subscription Form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Start Your Subscription
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubscribe} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>

                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    You'll be redirected to Stripe's secure checkout page to complete your subscription.
                  </AlertDescription>
                </Alert>

                <Button 
                  type="submit" 
                  className="w-full" 
                  disabled={loading || !email}
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <CreditCard className="h-4 w-4 mr-2" />
                      Subscribe Now
                    </>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center text-sm text-muted-foreground">
                <p>Secure payment processed by Stripe</p>
                <p className="mt-1">Cancel anytime from your account settings</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* FAQ Section */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Frequently Asked Questions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Can I cancel anytime?</h4>
              <p className="text-muted-foreground">
                Yes, you can cancel your subscription at any time. Your access will continue until the end of your current billing period.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Is my payment information secure?</h4>
              <p className="text-muted-foreground">
                Absolutely. We use Stripe for payment processing, which is trusted by millions of businesses worldwide and meets the highest security standards.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">What happens after I subscribe?</h4>
              <p className="text-muted-foreground">
                After successful payment, you'll gain immediate access to all premium features and receive a confirmation email.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 