import { useState } from "react";

function UploadPanel() {
  const [image, setImage] = useState(null);

  function handleImageChange(event) {
    const file = event.target.files[0];

    if (file) {
      setImage(file);
    }
  }

  return (
    <div>
      <h2>Upload Satellite Image</h2>

      <input
        type="file"
        accept="image/*"
        onChange={handleImageChange}
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
  );
}

export default UploadPanel;