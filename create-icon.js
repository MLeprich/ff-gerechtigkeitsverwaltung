const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');
const { default: pngToIco } = require('png-to-ico');

async function createIcon() {
    const sizes = [256, 128, 64, 48, 32, 16];
    const pngFiles = [];

    for (const size of sizes) {
        const canvas = createCanvas(size, size);
        const ctx = canvas.getContext('2d');

        // Red background with rounded corners (simplified - just red square)
        ctx.fillStyle = '#DC2626';
        ctx.fillRect(0, 0, size, size);

        // White "FF" text
        ctx.fillStyle = 'white';
        ctx.font = `bold ${Math.floor(size * 0.47)}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('FF', size / 2, size / 2 + size * 0.05);

        const pngPath = path.join(__dirname, 'build', `icon-${size}.png`);
        const buffer = canvas.toBuffer('image/png');
        fs.writeFileSync(pngPath, buffer);
        pngFiles.push(pngPath);
        console.log(`Created ${pngPath}`);
    }

    // Also save the 256px version as icon.png for electron-builder
    const mainPng = path.join(__dirname, 'build', 'icon.png');
    fs.copyFileSync(pngFiles[0], mainPng);
    console.log(`Created ${mainPng}`);

    // Convert to ICO
    try {
        const icoBuffer = await pngToIco(pngFiles);
        const icoPath = path.join(__dirname, 'build', 'icon.ico');
        fs.writeFileSync(icoPath, icoBuffer);
        console.log(`Created ${icoPath}`);
    } catch (err) {
        console.error('Error creating ICO:', err);
    }

    // Cleanup temporary files
    for (const file of pngFiles) {
        if (!file.endsWith('icon-256.png')) {
            fs.unlinkSync(file);
        }
    }
}

createIcon().catch(console.error);
