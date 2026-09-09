import { useEffect, useState } from "react";
import UploadPanel from "./UploadPanel";
import Terrain from "./Terrain";
import "./App.css";

const BACKEND_URL = "http://localhost:8000";

function App() {
  const [image, setImage] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);

  const [processData, setProcessData] = useState(null);

  const [depthMapUrl, setDepthMapUrl] = useState(null);

  const [terrainObjUrl, setTerrainObjUrl] = useState(null);
  const [terrainTextureUrl, setTerrainTextureUrl] = useState(null);

  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!image) {
      setImageUrl(null);
      return;
    }

    const url = URL.createObjectURL(image);

    setImageUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [image]);

  async function handleProcess(data) {
    if (!image) {
      alert("Please select an RGB image first.");
      return;
    }

    setProcessing(true);
    setError("");

    setProcessData(null);
    setDepthMapUrl(null);
    setTerrainObjUrl(null);
    setTerrainTextureUrl(null);

    const formData = new FormData();

    formData.append("file", image);

    /*
      Temporary hackathon behavior:

      Both Normal RGB and Georeferenced RGB currently
      use the working non-georeferenced pipeline.
    */

    formData.append("image_type", "normal");

    /*
      Keep track of what the user selected.
    */

    formData.append(
      "selected_mode",
      data.imageType
    );

    /*
      Geo data is collected for future implementation.
    */

    if (data.imageType === "georeferenced") {
      formData.append(
        "latitude",
        data.latitude
      );

      formData.append(
        "longitude",
        data.longitude
      );

      if (data.demFile) {
        formData.append(
          "dem_file",
          data.demFile
        );
      }
    }

    try {
      console.log("Selected mode:", data.imageType);
      console.log(
        "Current processing pipeline:",
        "non-georeferenced"
      );

      const response = await fetch(
        `${BACKEND_URL}/process`,
        {
          method: "POST",
          body: formData,
        }
      );

      let result = null;

      try {
        result = await response.json();
      } catch {
        result = null;
      }

      if (!response.ok) {
        throw new Error(
          result?.detail ||
            "Backend request failed."
        );
      }

      console.log(
        "Backend response:",
        result
      );

      /*
      =====================================================
      DEPTH / rDSM
      =====================================================
      */

      const depthPath =
        result?.relative_rdsm?.png_url ||
        result?.relative_depth?.png_url ||
        result?.refined_depth?.png_url ||
        result?.depth_map_url ||
        result?.depth_url;

      if (depthPath) {
        setDepthMapUrl(
          `${BACKEND_URL}${depthPath}`
        );
      }

      /*
      =====================================================
      TERRAIN OBJ
      =====================================================
      */

      const objPath =
        result?.mesh?.obj_url ||
        result?.obj_url ||
        result?.terrain_obj_url;

      if (objPath) {
        setTerrainObjUrl(
          `${BACKEND_URL}${objPath}`
        );
      }

      /*
      =====================================================
      TERRAIN TEXTURE
      =====================================================
      */

      const texturePath =
        result?.mesh?.texture_url ||
        result?.texture_url ||
        result?.terrain_texture_url;

      if (texturePath) {
        setTerrainTextureUrl(
          `${BACKEND_URL}${texturePath}`
        );
      }

      /*
      =====================================================
      SAVE RESULT
      =====================================================
      */

      setProcessData({
        ...result,
        ui_selected_mode: data.imageType,
        pipeline_used: "non-georeferenced",
      });

    } catch (err) {
      console.error(
        "Processing error:",
        err
      );

      setError(
        err?.message ||
          "Could not connect to the Geosculpt backend."
      );

    } finally {
      setProcessing(false);
    }
  }

  function handleNewImage() {
    setImage(null);
    setImageUrl(null);

    setProcessData(null);

    setDepthMapUrl(null);

    setTerrainObjUrl(null);
    setTerrainTextureUrl(null);

    setError("");
  }

  return (
    <div className="app">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="header">

        <div className="header-inner">
          <div className="brand">
            <div className="brand-name">
              Geosculpt
            </div>

            <div className="brand-subtitle">
              Single view height estimation and 3D visualization
            </div>
          </div>

        </div>

      </header>

      <main className="main">

        {/* =====================================================
            START SCREEN
        ===================================================== */}

        {!processData &&
          !processing && (

            <section className="start-screen">

              <div className="hero">

                <div className="hero-label">

                </div>

                <h1>
                  Upload an image
                </h1>

                <p>
                  Generate a depth representation and
                  3D terrain from a single RGB image.
                </p>

              </div>

              <div className="upload-card">

                <UploadPanel
                  onImageSelect={setImage}
                  onProcess={handleProcess}
                />

              </div>

            </section>

          )}

        {/* =====================================================
            PROCESSING SCREEN
        ===================================================== */}

        {processing && (

          <section className="processing-screen">

            <div className="processing-box">

              <div className="processing-label">
                GEOSCULPT
              </div>

              <div className="processing-line"></div>

              <h2>
                Generating terrain
              </h2>

              <p>
                Running depth estimation and building
                the 3D terrain model.
              </p>

            </div>

          </section>

        )}

        {/* =====================================================
            RESULTS
        ===================================================== */}

        {processData &&
          !processing && (

            <section className="results-screen">

              <div className="results-header">

                <div>

                  <div className="hero-label">
                    RECONSTRUCTION COMPLETE
                  </div>

                  <h1>
                    Terrain results
                  </h1>

                  <p>
                    Generated depth representation
                    and reconstructed terrain.
                  </p>

                </div>

                <button
                  className="new-image-button"
                  onClick={handleNewImage}
                >
                  Process another image
                </button>

              </div>

              <div className="image-results">

                {/* ORIGINAL IMAGE */}

                <div className="preview">

                  <div className="preview-header">

                    <div>
                      <h3>
                        Original image
                      </h3>

                      <p>
                        RGB input
                      </p>
                    </div>

                    <span>
                      RGB
                    </span>

                  </div>

                  <div className="preview-image">

                    {imageUrl ? (

                      <img
                        src={imageUrl}
                        alt="Original RGB"
                      />

                    ) : (

                      <span>
                        No image
                      </span>

                    )}

                  </div>

                </div>

                {/* DEPTH */}

                <div className="preview">

                  <div className="preview-header">

                    <div>
                      <h3>
                        Depth representation
                      </h3>

                      <p>
                        Relative rDSM output
                      </p>
                    </div>

                    <span>
                      rDSM
                    </span>

                  </div>

                  <div className="preview-image">

                    {depthMapUrl ? (

                      <img
                        key={depthMapUrl}
                        src={
                          `${depthMapUrl}?t=${Date.now()}`
                        }
                        alt="Generated relative rDSM"
                      />

                    ) : (

                      <span>
                        No depth map
                      </span>

                    )}

                  </div>

                </div>

              </div>

              {/* 3D TERRAIN */}

              <section className="terrain-section">

                <div className="terrain-header">

                  <div>

                    <div className="hero-label">
                      VISUALIZATION
                    </div>

                    <h2>
                      3D terrain
                    </h2>

                    <p>
                      Drag to rotate · Scroll to zoom
                    </p>

                  </div>

                  <span className="viewer-label">
                    LIVE VIEW
                  </span>

                </div>

                <div className="terrain-view">

                  {!terrainObjUrl ||
                  !terrainTextureUrl ? (

                    <div className="terrain-empty">
                      Terrain files not ready
                    </div>

                  ) : (

                    <Terrain
                      objUrl={terrainObjUrl}
                      textureUrl={terrainTextureUrl}
                    />

                  )}

                </div>

              </section>

              {/* STATUS */}

              <div className="status-bar">

                <span className="status-success">
                  ● Processing complete
                </span>

                {processData.depth_shape && (
                  <span>
                    Depth{" "}
                    {processData.depth_shape[0]}
                    {" × "}
                    {processData.depth_shape[1]}
                  </span>
                )}

                {processData.relative_rdsm && (
                  <span>
                    Relative rDSM{" "}
                    {Number(
                      processData.relative_rdsm.min
                    ).toFixed(2)}
                    {" – "}
                    {Number(
                      processData.relative_rdsm.max
                    ).toFixed(2)}
                  </span>
                )}

                {processData.mesh && (
                  <span>
                    Mesh{" "}
                    {processData.mesh.vertices}
                    {" "}vertices
                  </span>
                )}

              </div>

            </section>

          )}

        {/* ERROR */}

        {error &&
          !processing && (

            <div className="error-message">
              {error}
            </div>

          )}

      </main>

    </div>
  );
}

export default App;
