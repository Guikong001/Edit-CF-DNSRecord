addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const apiToken = API_TOKEN; // 从环境变量中获取API密钥
  const cfApiBaseUrl = 'https://api.cloudflare.com/client/v4';

  // 添加CORS头部的函数
  function addCorsHeaders(response) {
    const newHeaders = new Headers(response.headers)
    newHeaders.set('Access-Control-Allow-Origin', '*') // 或指定具体的域名
    newHeaders.set('Access-Control-Allow-Methods', 'POST, OPTIONS')
    newHeaders.set('Access-Control-Allow-Headers', 'Content-Type')
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    })
  }

  // 处理预检请求
  if (request.method === 'OPTIONS') {
    // 如果需要，可以在这里检查请求的头部，决定是否允许
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*', // 或指定您的前端域名
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    })
  }

  // 检查请求方法
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 })
  }

  // 解析请求体
  let requestData
  try {
    requestData = await request.json()
  } catch (e) {
    return new Response('Bad Request', { status: 400 })
  }

  const { action, recordType, domain, content, ttl, proxied } = requestData

  if (!action || !recordType || !domain) {
    return new Response('Missing required fields', { status: 400 })
  }

  // 获取Zone ID
  const baseDomain = getBaseDomain(domain)
  const zoneID = await getZoneID(baseDomain, apiToken, cfApiBaseUrl)
  if (!zoneID) {
    return new Response('Unable to get Zone ID', { status: 400 })
  }

  // 执行相应的操作
  let result
  switch (action) {
    case 'add':
      result = await addDNSRecord(zoneID, domain, recordType, content, ttl, proxied, apiToken, cfApiBaseUrl)
      break
    case 'update':
      result = await updateDNSRecord(zoneID, domain, recordType, content, ttl, proxied, apiToken, cfApiBaseUrl)
      break
    case 'delete':
      result = await deleteDNSRecord(zoneID, domain, recordType, apiToken, cfApiBaseUrl)
      break
    default:
      return new Response('Invalid action', { status: 400 })
  }

  let response = new Response(JSON.stringify(result), {
    status: result.success ? 200 : 500,
    headers: { 'Content-Type': 'application/json' }
  })

  // 添加CORS头部
  response = addCorsHeaders(response)

  return response
}

function getBaseDomain(domain) {
  const parts = domain.split('.')
  if (parts.length >= 2) {
    return parts.slice(-2).join('.')
  }
  return domain
}

async function getZoneID(baseDomain, apiToken, cfApiBaseUrl) {
  const url = `${cfApiBaseUrl}/zones?name=${baseDomain}`
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    }
  })
  const data = await response.json()
  if (data.success && data.result.length > 0) {
    return data.result[0].id
  }
  return null
}

async function getDNSRecordID(zoneID, recordName, recordType, apiToken, cfApiBaseUrl) {
  const url = `${cfApiBaseUrl}/zones/${zoneID}/dns_records?type=${recordType}&name=${recordName}`
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    }
  })
  const data = await response.json()
  if (data.success && data.result.length > 0) {
    return data.result[0].id
  }
  return null
}

async function addDNSRecord(zoneID, recordName, recordType, content, ttl, proxied, apiToken, cfApiBaseUrl) {
  const url = `${cfApiBaseUrl}/zones/${zoneID}/dns_records`
  const payload = {
    type: recordType,
    name: recordName,
    content: content,
    ttl: ttl
  }
  if (['A', 'AAAA', 'CNAME'].includes(recordType)) {
    payload.proxied = proxied
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  const data = await response.json()
  return data
}

async function updateDNSRecord(zoneID, recordName, recordType, content, ttl, proxied, apiToken, cfApiBaseUrl) {
  const recordID = await getDNSRecordID(zoneID, recordName, recordType, apiToken, cfApiBaseUrl)
  if (!recordID) {
    return { success: false, errors: [{ message: 'DNS Record not found' }] }
  }
  const url = `${cfApiBaseUrl}/zones/${zoneID}/dns_records/${recordID}`
  const payload = {
    type: recordType,
    name: recordName,
    content: content,
    ttl: ttl
  }
  if (['A', 'AAAA', 'CNAME'].includes(recordType)) {
    payload.proxied = proxied
  }
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  const data = await response.json()
  return data
}

async function deleteDNSRecord(zoneID, recordName, recordType, apiToken, cfApiBaseUrl) {
  const recordID = await getDNSRecordID(zoneID, recordName, recordType, apiToken, cfApiBaseUrl)
  if (!recordID) {
    return { success: false, errors: [{ message: 'DNS Record not found' }] }
  }
  const url = `${cfApiBaseUrl}/zones/${zoneID}/dns_records/${recordID}`
  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json'
    }
  })
  const data = await response.json()
  return data
}
