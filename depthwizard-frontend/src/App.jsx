import { useEffect, useState } from "react";

import UploadPanel from "./UploadPanel";
import Terrain from "./Terrain";

import "./App.css";

const DEMO_BASE = `${import.meta.env.BASE_URL}demo/`;

const DEMO_IMAGE = `${DEMO_BASE}demo-image.jpg`;
const DEMO_DEPTH = `${DEMO_BASE}demo-depth.png`;
const DEMO_OBJ = `${DEMO_BASE}terrain.obj`;
const DEMO_TEXTURE = `${DEMO_BASE}texture.jpg`;

function App() {
  const [image, setImage] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);

  const [processData, setProcessData] = useState(null);

  const [depthMapUrl, setDepthMapUrl] = useState(null);

  const [terrainObjUrl, setTerrainObjUrl] = useState(null);
  const [terrainTextureUrl, setTerrainTextureUrl] =
    useState(null);

  const [processing, setProcessing] = useState(false);

  const [error, setError] = useState("");

  const [cloudUnavailable, setCloudUnavailable] =
    useState(false);


  /* =====================================================
     LOCAL IMAGE PREVIEW
  ===================================================== */

  useEffect(() => {
    if (!image) {
      return;
    }

    const url = URL.createObjectURL(image);

    setImageUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [image]);


  /* =====================================================
     IMAGE SELECT
  ===================================================== */

  function handleImageSelect(file) {
    setImage(file);

    setCloudUnavailable(false);
    setProcessData(null);

    setDepthMapUrl(null);
    setTerrainObjUrl(null);
    setTerrainTextureUrl(null);

    setError("");
  }


  /* =====================================================
     PROCESS IMAGE

     Cloud inference is currently unavailable.
  ===================================================== */

  async function handleProcess() {
    if (!image) {
      alert("Please select an RGB image first.");
      return;
    }

    setProcessing(false);

    setProcessData(null);

    setDepthMapUrl(null);
    setTerrainObjUrl(null);
    setTerrainTextureUrl(null);

    setError("");

    /*
      Open the professional maintenance page.
    */

    setCloudUnavailable(true);
  }


  /* =====================================================
     SEE DEMO
  ===================================================== */

  function handleSeeDemo() {
    setCloudUnavailable(false);

    setProcessing(false);

    setError("");

    /*
      Use the pre-generated demo image.
    */

    setImage(null);

    setImageUrl(DEMO_IMAGE);

    /*
      Pre-generated depth result.
    */

    setDepthMapUrl(DEMO_DEPTH);

    /*
      Existing Terrain.jsx will load these.
    */

    setTerrainObjUrl(DEMO_OBJ);

    setTerrainTextureUrl(DEMO_TEXTURE);

    /*
      Make the existing results screen
      display the demo exactly like a
      completed reconstruction.
    */

    setProcessData({
      status: "success",

      scene_name:
        "GeoSculpt Demo Terrain",

      pipeline_used:
        "pre-generated-demo",

      uploaded_filename:
        "GeoSculpt Demo",

      depth_shape: null,

      mesh: {
        vertices:
          "Pre-generated",
      },

      resolved_urls: {
        depth:
          DEMO_DEPTH,

        terrain_obj:
          DEMO_OBJ,

        terrain_texture:
          DEMO_TEXTURE,
      },
    });
  }


  /* =====================================================
     BACK FROM MAINTENANCE
  ===================================================== */

  function handleBackToUpload() {
    setCloudUnavailable(false);

    setError("");
  }


  /* =====================================================
     NEW IMAGE
  ===================================================== */

  function handleNewImage() {
    setImage(null);

    setImageUrl(null);

    setProcessData(null);

    setDepthMapUrl(null);

    setTerrainObjUrl(null);

    setTerrainTextureUrl(null);

    setCloudUnavailable(false);

    setError("");
  }


  /* =====================================================
     UI
  ===================================================== */

  return (
    <div className="app">

      {/* =================================================
          HEADER
      ================================================= */}

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


        {/* =================================================
            CLOUD MAINTENANCE PAGE
        ================================================= */}

        {cloudUnavailable && (
          <section className="maintenance-screen">

            <div className="maintenance-content">

               <div className="maintenance-status">
                SERVICE STATUS
              </div> 


              <div className="maintenance-icon">
                <div className="maintenance-icon-line" />
                <div className="maintenance-icon-dot" />
              </div> 


              <h1>
                Cloud inference is
                <br />
                temporarily unavailable.
              </h1>


              <p className="maintenance-description">
                We can't process new images at the moment
                because the cloud inference service has
                reached its current processing limit.
              </p>


            
              <div className="maintenance-actions">

                <button
                  className="maintenance-demo-button"
                  onClick={handleSeeDemo}
                >
                  See Demo
                </button>


                <button
                  className="maintenance-back-button"
                  onClick={handleBackToUpload}
                >
                  Back to upload
                </button>

              </div>


              

            </div>

          </section>
        )}


        {/* =================================================
            START SCREEN
        ================================================= */}

        {!cloudUnavailable &&
          !processData &&
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
                  onImageSelect={
                    handleImageSelect
                  }

                  onProcess={
                    handleProcess
                  }

                  onSeeDemo={
                    handleSeeDemo
                  }
                />

              </div>

            </section>

          )}


        {/* =================================================
            PROCESSING SCREEN
        ================================================= */}

        {processing && (

          <section className="processing-screen">

            <div className="processing-box">

              <div className="processing-label">
                GEOSCULPT
              </div>

              <div className="processing-line">
              </div>

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


        {/* =================================================
            RESULTS
        ================================================= */}

        {processData &&
          !processing &&
          !cloudUnavailable && (

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
                  onClick={
                    handleNewImage
                  }
                >
                  Process another image
                </button>

              </div>


              {/* ==========================================
                  IMAGE RESULTS
              ========================================== */}

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


                {/* DEPTH MAP */}

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
                        src={depthMapUrl}
                        alt="Generated relative rDSM"
                      />

                    ) : (

                      <span>
                        No depth map generated
                      </span>

                    )}

                  </div>

                </div>

              </div>


              {/* ==========================================
                  3D TERRAIN
              ========================================== */}

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

                      <div>
                        Terrain files not ready
                      </div>

                      <small>
                        Waiting for terrain output.
                      </small>

                    </div>

                  ) : (

                    <Terrain
                      key={`${terrainObjUrl}-${terrainTextureUrl}`}
                      objUrl={terrainObjUrl}
                      textureUrl={terrainTextureUrl}
                    />

                  )}

                </div>

              </section>


              {/* ==========================================
                  STATUS
              ========================================== */}

              <div className="status-bar">

                <span className="status-success">
                  ✓ Processing complete
                </span>


                {processData.scene_name && (

                  <span>
                    Scene{" "}
                    {processData.scene_name}
                  </span>

                )}


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


        {/* =================================================
            ERROR
        ================================================= */}

        {error &&
          !processing &&
          !cloudUnavailable && (

            <div className="error-message">
              {error}
            </div>

          )}

      </main>

    </div>
  );
}

export default App;