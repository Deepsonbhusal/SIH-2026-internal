import { useState } from "react";
import UploadPanel from "./UploadPanel";
import Terrain from "./Terrain";

function App() {
  const [image, setImage] = useState(null);

  async function handleProcess() {
    if (!image) {
      alert("Please select an image first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", image);

    const response = await fetch("http://localhost:8000/process", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    console.log(result);
  }

  return (
    <div>
      <h1>DepthWizard</h1>

      <div style={{ display: "flex", gap: "20px" }}>
        <div style={{ width: "40%" }}>
          <UploadPanel
            onImageSelect={setImage}
            onProcess={handleProcess}
          />

          {image && (
            <div>
              <h3>Preview</h3>

              <img
                src={URL.createObjectURL(image)}
                alt="Satellite preview"
                width="400"
              />
            </div>
          )}
        </div>

        <div style={{ width: "100%", height: "1000px" }}>
          <Terrain />
        </div>
      </div>
    </div>
  );
}

export default App;