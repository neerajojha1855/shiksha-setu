import { AuthPage } from "./features/auth/AuthPage";
import { NeedsDiscoveryPage } from "./features/needs/NeedsDiscoveryPage";

export function App() {
  if (window.location.pathname.startsWith("/needs")) {
    return <NeedsDiscoveryPage />;
  }
  return <AuthPage />;
}

export default App;
