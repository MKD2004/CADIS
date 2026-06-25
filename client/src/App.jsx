import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import StaggeredMenu from "./components/StaggeredMenu";
import DarkVeil from "./components/DarkVeil";
import TargetCursor from "./components/TargetCursor";
import Home from "./pages/Home";
import Analyze from "./pages/Analyze";
import Module1 from "./pages/Module1";
import Module2 from "./pages/Module2";
import Module3 from "./pages/Module3";
import Module4 from "./pages/Module4";
import Module5 from "./pages/Module5";
import Module6 from "./pages/Module6";

const menuItems = [
  { label: "Home", ariaLabel: "Go to home page", link: "/" },
  { label: "Analyze", ariaLabel: "Upload & Analyze", link: "/analyze" },
  { label: "Preprocessing", ariaLabel: "NLP Preprocessing", link: "/module-1" },
  { label: "Embeddings", ariaLabel: "Semantic Embeddings", link: "/module-2" },
  { label: "NER + IE", ariaLabel: "Named Entity Recognition", link: "/module-3" },
  { label: "Ambiguity", ariaLabel: "Ambiguity Resolution", link: "/module-4" },
  { label: "QA Engine", ariaLabel: "Question Answering", link: "/module-5" },
  { label: "Summary", ariaLabel: "Summary Generator", link: "/module-6" },
];

const socialItems = [
  { label: "GitHub", link: "https://github.com/MKD2004/CADIS" },
  { label: "LinkedIn", link: "https://linkedin.com" },
];

export default function App() {
  return (
    <div className="min-h-screen relative">
      <TargetCursor
        spinDuration={2}
        hideDefaultCursor={false}
        parallaxOn={true}
        cursorColor="#ffffff"
        cursorColorOnTarget="#298DFF"
      />
      <div className="fixed inset-0 z-0 pointer-events-none">
        <DarkVeil
          speed={0.3}
          hueShift={350}
          noiseIntensity={0}
          warpAmount={0.4}
          resolutionScale={1}
        />
      </div>

      <Navbar />
      <StaggeredMenu
        position="left"
        items={menuItems}
        socialItems={socialItems}
        displaySocials={true}
        displayItemNumbering={true}
        menuButtonColor="#ffffff"
        openMenuButtonColor="#fff"
        changeMenuColorOnOpen={true}
        colors={["#141420", "#298DFF"]}
        accentColor="#298DFF"
        isFixed={true}
      />
      <main className="relative z-10 pt-14">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/module-1" element={<Module1 />} />
          <Route path="/module-2" element={<Module2 />} />
          <Route path="/module-3" element={<Module3 />} />
          <Route path="/module-4" element={<Module4 />} />
          <Route path="/module-5" element={<Module5 />} />
          <Route path="/module-6" element={<Module6 />} />
        </Routes>
      </main>
    </div>
  );
}
