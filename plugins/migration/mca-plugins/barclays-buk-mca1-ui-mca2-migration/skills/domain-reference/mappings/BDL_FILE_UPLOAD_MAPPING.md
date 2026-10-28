# BDL_FILE_UPLOAD_MAPPING.md

## Overview

Maps `<mca-file-upload>` to Blueprint-React `DragDrop` (for drag-and-drop zones) or `ButtonLabel` + hidden `<input type="file">` (for button-style upload triggers), plus `SimpleFileUpload` for displaying upload status.

## MCA1 Pattern

```html
<mca-file-upload
  text="Upload Button"
  name="file_name"
  id="v_file-upload"
  class=""
>
</mca-file-upload>
```

### JavaScript API

```javascript
var objFileUpload = $('#file-upload-jQuery-selector').getComponent();

// Event: triggered when file is selected
objFileUpload.onchange = function(eve) {
  console.log(eve);
};

// Get selected file value
objFileUpload.value();
```

### Attributes

| Attribute | Description | Default |
|-----------|-------------|---------|
| `text` | Button label text | — |
| `name` | Form field name for the file input | — |
| `id` | Element ID (MANDATORY) | — |
| `class` | CSS class | — |

---

## Blueprint-React Equivalent

### Pattern 1: Drag-and-Drop Upload Zone

```typescript
import React, { useState } from 'react';
import { DragDrop, SimpleFileUpload, Type, Icon, ProgressBar } from '@barclays/blueprint-react';

interface UploadState {
  file: File | null;
  state: 'idle' | 'in-progress' | 'success' | 'error';
  progress: number;
  errorMessage?: string;
}

export const FileUploadSection: React.FC = () => {
  const [upload, setUpload] = useState<UploadState>({ file: null, state: 'idle', progress: 0 });

  const handleFiles = (files: File[]) => {
    if (files.length > 0) {
      setUpload({ file: files[0], state: 'in-progress', progress: 0 });
      // Trigger upload logic here
    }
  };

  return (
    <>
      {upload.state === 'idle' && (
        <DragDrop setter={handleFiles} buttonText="Choose file">
          <Type>Drag file here or click to browse</Type>
        </DragDrop>
      )}

      {upload.file && upload.state !== 'idle' && (
        <SimpleFileUpload
          state={upload.state === 'in-progress' ? 'in-progress' : upload.state}
          fileName={<Type weight="medium">{upload.file.name}</Type>}
          fileSize={<Type size="sm">{formatFileSize(upload.file.size)}</Type>}
          progressBar={
            upload.state === 'in-progress'
              ? <ProgressBar percent={upload.progress} status="info"><Type size="sm">Uploading...</Type></ProgressBar>
              : undefined
          }
          successIcon={upload.state === 'success' ? <Icon icon="success-fill" size="sm" status="success" /> : undefined}
          errorIcon={upload.state === 'error' ? <Icon icon="error-fill" size="sm" status="error" /> : undefined}
          errorMessage={upload.errorMessage ? <Type size="sm" color="error">{upload.errorMessage}</Type> : undefined}
        />
      )}
    </>
  );
};
```

### Pattern 2: Button-Style Upload (matches MCA1 default behavior)

```typescript
import React, { useRef, useState } from 'react';
import { Button, SimpleFileUpload, Type, Icon } from '@barclays/blueprint-react';

export const FileUploadButton: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        name="file_name"
        style={{ display: 'none' }}
        onChange={handleChange}
        aria-hidden="true"
      />
      <Button variant="primary" onClick={handleClick}>
        Upload Button
      </Button>

      {selectedFile && (
        <SimpleFileUpload
          state="success"
          fileName={<Type weight="medium">{selectedFile.name}</Type>}
          fileSize={<Type size="sm">{formatFileSize(selectedFile.size)}</Type>}
          successIcon={<Icon icon="success-fill" size="sm" status="success" />}
        />
      )}
    </>
  );
};
```

---

## Attribute Mapping

| MCA1 Attribute | Blueprint-React Equivalent | Notes |
|----------------|---------------------------|-------|
| `text` | `buttonText` prop on `DragDrop` OR `Button` children | Button label text |
| `name` | `name` prop on hidden `<input type="file">` | Form field name |
| `id` | `id` prop on container element | For accessibility |
| `class` | Not needed | Blueprint handles styling |

## API Mapping

| MCA1 jQuery API | React Equivalent | Notes |
|-----------------|-----------------|-------|
| `.getComponent()` | Not needed | Direct component reference via React |
| `.onchange = fn` | `onChange` on hidden `<input>` OR `setter` on `DragDrop` | Callback receives files |
| `.value()` | `selectedFile` state variable | Access via React state |

---

## Iron Rules

1. **DragDrop is the upload zone, SimpleFileUpload is the status display** — they are two separate components, not one
2. **Never use `<input type="file">` visible** — always hidden behind a Button or DragDrop trigger
3. **SimpleFileUpload requires all three**: `fileName`, `fileSize`, and `state` — all are mandatory props
4. **DragDrop `setter` receives `File[]`** — always an array even for single file upload
