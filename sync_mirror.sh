#!/bin/bash
echo "🔄 Sincronizando lbh-image-validator..."
git push origin main
git push github main
echo "✅ Sincronización exitosa"
