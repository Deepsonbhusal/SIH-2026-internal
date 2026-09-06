import UploadPanel from "./UploadPanel";
import Terrain from "./Terrain";

function App() {
  return (
    <div>
      <h1>DepthWizard</h1>

      <div style={{ display: "flex", gap: "20px" }}>
        <div style={{ width: "40%" }}>
          <UploadPanel />
        </div>

        <div style={{ width: "60%", height: "600px" }}>
          <Terrain />
        </div>
      </div>
    </div>
  );
}

export default App;