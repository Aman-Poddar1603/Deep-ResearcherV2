import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Home, ArrowLeft } from "lucide-react"

const NotFound = () => {
    const navigate = useNavigate()

    return (
        <div className="min-h-[80vh] w-full flex flex-col items-center justify-center p-4 text-center animate-in fade-in zoom-in duration-500">

            <div className="relative z-10 max-w-2xl w-full space-y-8">
                {/* 404 Visual */}
                <div className="relative flex justify-center items-center">
                    <h1 className="text-[12rem] md:text-[16rem] font-black text-foreground/5 select-none leading-none">
                        404
                    </h1>
                </div>

                <div className="space-y-4">
                    <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">
                        Lost in the digital void?
                    </h2>
                    <p className="text-muted-foreground text-lg md:text-xl max-w-md mx-auto leading-relaxed">
                        The page you're looking for has vanished into thin air. Let's get you back to familiar territory.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                    <Button
                        variant="default"
                        size="lg"
                        className="w-full sm:w-auto px-8 py-6 rounded-xl hover:scale-105 transition-transform"
                        onClick={() => navigate("/")}
                    >
                        <Home className="mr-2 h-5 w-5" />
                        Go Home
                    </Button>
                    <Button
                        variant="outline"
                        size="lg"
                        className="w-full sm:w-auto px-8 py-6 rounded-xl hover:bg-muted/50 border-muted-foreground/20 transition-all"
                        onClick={() => navigate(-1)}
                    >
                        <ArrowLeft className="mr-2 h-5 w-5" />
                        Go Back
                    </Button>
                </div>
            </div>
        </div>
    )
}

export default NotFound