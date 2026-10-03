# PROJECT: ISIRA Master Engine
# COMPONENT: Security Vault (Direct Key Authentication)
# ARCHITECT: Guggilla Prashanth
# STATUS: Verified & Ready for Gemini 2.5 Flash

class ISIRASecurity:
    def _init_(self):
        pass

    def get_secret(self, secret_id: str):
        """
        Returns the specific API key for the ISIRA engine.
        This version uses the dedicated Digital Daari Gemini API Key.
        """
        # Optimized for Gemini 2.5 Flash High-Speed Inference
        return "AIzaSyC4XrJtX6ZNHbLLkMOG9icxvy3eVHIW9hc"