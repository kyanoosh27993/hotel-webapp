import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

const img = fs.readFileSync('/home/z/my-project/upload/IMG_20261116_164826.jpg');
const dataUrl = `data:image/jpeg;base64,${img.toString('base64')}`;

const zai = await ZAI.create();
const prompt = "Convert this photo into a formal passport-style personnel ID photo: crop to show only the man's head and shoulders (face close-up, no desk, no phone, no glasses, no office furniture visible), pure white background, even soft studio lighting, subject facing the camera directly with a neutral expression, keep the same person's face, beard, slicked-back hairstyle, white shirt and dark vest exactly unchanged, photorealistic professional portrait";
const response = await zai.images.generations.edit({
  prompt,
  images: [{ url: dataUrl }],
  size: '864x1152'
});
const b64 = response.data[0].base64;
fs.writeFileSync('/home/z/my-project/download/personnel_photo_3x4.png', Buffer.from(b64, 'base64'));
console.log('saved');
