import { Button } from './ui/button'

type Props = {
  presentationUrl: string
  presentationName?: string
  onClose?: () => void
}

export function SuccessPage({ presentationUrl, presentationName, onClose }: Props) {
  const handlePreview = () => {
    window.open(presentationUrl, '_blank')
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
      <div className="text-center space-y-4">
        {/* Success Icon */}
        <div className="mx-auto w-16 h-16 bg-green-500 rounded-full flex items-center justify-center">
          <svg
            className="w-10 h-10 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        {/* Success Message */}
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-white">Presentation Generated Successfully!</h2>
          <p className="text-white/70 text-lg">
            Your presentation "{presentationName || 'Presentation'}" has been created.
          </p>
        </div>

        {/* Preview Button */}
        <div className="pt-4">
          <button
            onClick={handlePreview}
            className="inline-flex items-center justify-center rounded-md bg-green-500 text-white px-8 py-3 font-semibold text-lg hover:bg-green-600 transition-colors shadow-lg shadow-green-500/30"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              />
            </svg>
            Preview
          </button>
        </div>

        {/* Additional Info */}
        <p className="text-white/50 text-sm pt-2">
          Click the button above to open your presentation in Google Slides
        </p>

        {/* Create Another Button */}
        {onClose && (
          <div className="pt-4">
            <button
              onClick={onClose}
              className="text-white/60 hover:text-white text-sm underline transition-colors"
            >
              Create Another Presentation
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

