<?php

define('_CATROWEB_INDEX', 1);
include_once "config.inc.php";
$db = new mysqli('localhost', $db_user, $db_password, $db_name);

if ($db->connect_errno)
{
  http_response_code(500);
  header("Content-Type: text/plain");
  echo "Failed opening database." . PHP_EOL;
  echo $db->connect_error . PHP_EOL;
  exit(2);
}

function show_db_failure()
{
  global $db;
  http_response_code(500);
  header("Content-Type: text/plain");
  echo "Failed executing query." . PHP_EOL;
  echo $db->error . PHP_EOL;
  exit(3);
}

$res = $db->query("SELECT `label`, `type`, `source_sha`, `deployed_at`, `title`, `url`, `author`, `fail_count` FROM `deployment` ORDER BY `type` DESC, `deployed_at` DESC");
if (!$res)
{
  show_db_failure();
}
while ($row = $res->fetch_assoc())
{
  if ($row['fail_count'] != 0)
  {
    $fail_data[] = $row;
  }
  else
  {
    $data[] = $row;
  }
}

$db->close();
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"
          integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">
    <title>Catroweb Test Deployments</title>
    <style>
        body
        {
            padding-top: 1rem;
        }

        p.logo, h1
        {
            text-align: center;
        }

        p.logo img
        {
            width: 100%;
            max-width: 250px;
        }

        code.hash
        {
            max-width: 100px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: inline-block;
        }

        .actions a
        {
            text-decoration: none;
        }

    </style>
</head>
<body>
<div class="container">
    <p class="logo"><img src="https://share.catrob.at/images/logo/catrobat_text.svg" alt="Catrobat Logo"/></p>
    <h1>Catroweb Test Deployments</h1>

  <?php $label = explode('.', $_SERVER['HTTP_HOST'])[0];
  if ($label !== "index"): ?>
      <div class="alert alert-warning mt-4">
          Deployment with label <code><?php echo $label; ?></code> was not found.
      </div>
  <?php endif; ?>
    <table class="table table-responsive-md mt-4">
        <thead>
        <tr>
            <th scope="col">Label</th>
            <th scope="col">Type</th>
            <th scope="col">Title</th>
            <th scope="col">Author</th>
            <th scope="col">Commit</th>
            <th scope="col">Deploy Date (UTC)</th>
            <th scope="col"></th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($data as $entry): ?>
          <?php $url = sprintf($url_template, $entry['label']); ?>
            <tr>
                <td><a href="<?php echo $url; ?>"><?php echo $entry['label']; ?></a></td>
                <td>
                  <?php if ($entry['type'] == 'pr'): ?>
                      <svg viewBox="0 0 12 16" width="12" height="16" aria-hidden="true">
                          <path fill-rule="evenodd"
                                d="M11 11.28V5c-.03-.78-.34-1.47-.94-2.06C9.46 2.35 8.78 2.03 8 2H7V0L4 3l3 3V4h1c.27.02.48.11.69.31.21.2.3.42.31.69v6.28A1.993 1.993 0 0010 15a1.993 1.993 0 001-3.72zm-1 2.92c-.66 0-1.2-.55-1.2-1.2 0-.65.55-1.2 1.2-1.2.65 0 1.2.55 1.2 1.2 0 .65-.55 1.2-1.2 1.2zM4 3c0-1.11-.89-2-2-2a1.993 1.993 0 00-1 3.72v6.56A1.993 1.993 0 002 15a1.993 1.993 0 001-3.72V4.72c.59-.34 1-.98 1-1.72zm-.8 10c0 .66-.55 1.2-1.2 1.2-.65 0-1.2-.55-1.2-1.2 0-.65.55-1.2 1.2-1.2.65 0 1.2.55 1.2 1.2zM2 4.2C1.34 4.2.8 3.65.8 3c0-.65.55-1.2 1.2-1.2.65 0 1.2.55 1.2 1.2 0 .65-.55 1.2-1.2 1.2z"></path>
                      </svg> PR
                  <?php elseif ($entry['type'] == 'branch'): ?>
                      <svg viewBox="0 0 10 16" width="10" height="16" aria-hidden="true">
                          <path fill-rule="evenodd"
                                d="M10 5c0-1.11-.89-2-2-2a1.993 1.993 0 00-1 3.72v.3c-.02.52-.23.98-.63 1.38-.4.4-.86.61-1.38.63-.83.02-1.48.16-2 .45V4.72a1.993 1.993 0 00-1-3.72C.88 1 0 1.89 0 3a2 2 0 001 1.72v6.56c-.59.35-1 .99-1 1.72 0 1.11.89 2 2 2 1.11 0 2-.89 2-2 0-.53-.2-1-.53-1.36.09-.06.48-.41.59-.47.25-.11.56-.17.94-.17 1.05-.05 1.95-.45 2.75-1.25S8.95 7.77 9 6.73h-.02C9.59 6.37 10 5.73 10 5zM2 1.8c.66 0 1.2.55 1.2 1.2 0 .65-.55 1.2-1.2 1.2C1.35 4.2.8 3.65.8 3c0-.65.55-1.2 1.2-1.2zm0 12.41c-.66 0-1.2-.55-1.2-1.2 0-.65.55-1.2 1.2-1.2.65 0 1.2.55 1.2 1.2 0 .65-.55 1.2-1.2 1.2zm6-8c-.66 0-1.2-.55-1.2-1.2 0-.65.55-1.2 1.2-1.2.65 0 1.2.55 1.2 1.2 0 .65-.55 1.2-1.2 1.2z"></path>
                      </svg> Branch
                  <?php else: ?>
                    <?php echo $entry['type']; ?>
                  <?php endif; ?>
                </td>
                <td><?php echo $entry['title']; ?></td>
                <td><?php echo $entry['author']; ?></td>
                <td><code class="hash"
                          alt="<?php echo $entry['source_sha']; ?>"><?php echo $entry['source_sha']; ?></code></td>
                <td><?php echo $entry['deployed_at']; ?></td>
                <td class="actions">
                    <a href="<?php echo $url; ?>" class="mr-2">
                        <svg aria-hidden="true" height="25" viewBox="0 0 512 512">
                            <path fill="currentColor"
                                  d="M432,320H400a16,16,0,0,0-16,16V448H64V128H208a16,16,0,0,0,16-16V80a16,16,0,0,0-16-16H48A48,48,0,0,0,0,112V464a48,48,0,0,0,48,48H400a48,48,0,0,0,48-48V336A16,16,0,0,0,432,320ZM488,0h-128c-21.37,0-32.05,25.91-17,41l35.73,35.73L135,320.37a24,24,0,0,0,0,34L157.67,377a24,24,0,0,0,34,0L435.28,133.32,471,169c15,15,41,4.5,41-17V24A24,24,0,0,0,488,0Z"></path>
                        </svg>
                    </a>
                    <a href="<?php echo $entry['url']; ?>">
                        <svg aria-hidden="true" height="25" viewBox="0 0 496 512">
                            <path fill="currentColor"
                                  d="M165.9 397.4c0 2-2.3 3.6-5.2 3.6-3.3.3-5.6-1.3-5.6-3.6 0-2 2.3-3.6 5.2-3.6 3-.3 5.6 1.3 5.6 3.6zm-31.1-4.5c-.7 2 1.3 4.3 4.3 4.9 2.6 1 5.6 0 6.2-2s-1.3-4.3-4.3-5.2c-2.6-.7-5.5.3-6.2 2.3zm44.2-1.7c-2.9.7-4.9 2.6-4.6 4.9.3 2 2.9 3.3 5.9 2.6 2.9-.7 4.9-2.6 4.6-4.6-.3-1.9-3-3.2-5.9-2.9zM244.8 8C106.1 8 0 113.3 0 252c0 110.9 69.8 205.8 169.5 239.2 12.8 2.3 17.3-5.6 17.3-12.1 0-6.2-.3-40.4-.3-61.4 0 0-70 15-84.7-29.8 0 0-11.4-29.1-27.8-36.6 0 0-22.9-15.7 1.6-15.4 0 0 24.9 2 38.6 25.8 21.9 38.6 58.6 27.5 72.9 20.9 2.3-16 8.8-27.1 16-33.7-55.9-6.2-112.3-14.3-112.3-110.5 0-27.5 7.6-41.3 23.6-58.9-2.6-6.5-11.1-33.3 2.6-67.9 20.9-6.5 69 27 69 27 20-5.6 41.5-8.5 62.8-8.5s42.8 2.9 62.8 8.5c0 0 48.1-33.6 69-27 13.7 34.7 5.2 61.4 2.6 67.9 16 17.7 25.8 31.5 25.8 58.9 0 96.5-58.9 104.2-114.8 110.5 9.2 7.9 17 22.9 17 46.4 0 33.7-.3 75.4-.3 83.6 0 6.5 4.6 14.4 17.3 12.1C428.2 457.8 496 362.9 496 252 496 113.3 383.5 8 244.8 8zM97.2 352.9c-1.3 1-1 3.3.7 5.2 1.6 1.6 3.9 2.3 5.2 1 1.3-1 1-3.3-.7-5.2-1.6-1.6-3.9-2.3-5.2-1zm-10.8-8.1c-.7 1.3.3 2.9 2.3 3.9 1.6 1 3.6.7 4.3-.7.7-1.3-.3-2.9-2.3-3.9-2-.6-3.6-.3-4.3.7zm32.4 35.6c-1.6 1.3-1 4.3 1.3 6.2 2.3 2.3 5.2 2.6 6.5 1 1.3-1.3.7-4.3-1.3-6.2-2.2-2.3-5.2-2.6-6.5-1zm-11.4-14.7c-1.6 1-1.6 3.6 0 5.9 1.6 2.3 4.3 3.3 5.6 2.3 1.6-1.3 1.6-3.9 0-6.2-1.4-2.3-4-3.3-5.6-2z"></path>
                        </svg>
                    </a>

                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
  <?php if (count($fail_data)): ?>
      <h3>Failed deploying the following pull requests</h3>
      <table class="table table-responsive-md mt-4">
          <thead>
          <tr>
              <th scope="col">Label</th>
              <th scope="col">Title</th>
              <th scope="col">Author</th>
              <th scope="col">Commit</th>
              <th scope="col">Deploy Date (UTC)</th>
              <th scope="col">Fail Count</th>
              <th scope="col"></th>
          </tr>
          </thead>
          <tbody>
          <?php foreach ($fail_data as $entry): ?>
            <?php $url = sprintf($url_template, $entry['label']); ?>
              <tr>
                  <td><?php echo $entry['label']; ?></td>
                  <td><?php echo $entry['title']; ?></td>
                  <td><?php echo $entry['author']; ?></td>
                  <td><code class="hash"
                            alt="<?php echo $entry['source_sha']; ?>"><?php echo $entry['source_sha']; ?></code></td>
                  <td><?php echo $entry['deployed_at']; ?></td>
                  <td><?php echo $entry['fail_count']; ?></td>
                  <td class="actions">
                      <a href="<?php echo $entry['url']; ?>">
                          <svg aria-hidden="true" height="25" viewBox="0 0 496 512">
                              <path fill="currentColor"
                                    d="M165.9 397.4c0 2-2.3 3.6-5.2 3.6-3.3.3-5.6-1.3-5.6-3.6 0-2 2.3-3.6 5.2-3.6 3-.3 5.6 1.3 5.6 3.6zm-31.1-4.5c-.7 2 1.3 4.3 4.3 4.9 2.6 1 5.6 0 6.2-2s-1.3-4.3-4.3-5.2c-2.6-.7-5.5.3-6.2 2.3zm44.2-1.7c-2.9.7-4.9 2.6-4.6 4.9.3 2 2.9 3.3 5.9 2.6 2.9-.7 4.9-2.6 4.6-4.6-.3-1.9-3-3.2-5.9-2.9zM244.8 8C106.1 8 0 113.3 0 252c0 110.9 69.8 205.8 169.5 239.2 12.8 2.3 17.3-5.6 17.3-12.1 0-6.2-.3-40.4-.3-61.4 0 0-70 15-84.7-29.8 0 0-11.4-29.1-27.8-36.6 0 0-22.9-15.7 1.6-15.4 0 0 24.9 2 38.6 25.8 21.9 38.6 58.6 27.5 72.9 20.9 2.3-16 8.8-27.1 16-33.7-55.9-6.2-112.3-14.3-112.3-110.5 0-27.5 7.6-41.3 23.6-58.9-2.6-6.5-11.1-33.3 2.6-67.9 20.9-6.5 69 27 69 27 20-5.6 41.5-8.5 62.8-8.5s42.8 2.9 62.8 8.5c0 0 48.1-33.6 69-27 13.7 34.7 5.2 61.4 2.6 67.9 16 17.7 25.8 31.5 25.8 58.9 0 96.5-58.9 104.2-114.8 110.5 9.2 7.9 17 22.9 17 46.4 0 33.7-.3 75.4-.3 83.6 0 6.5 4.6 14.4 17.3 12.1C428.2 457.8 496 362.9 496 252 496 113.3 383.5 8 244.8 8zM97.2 352.9c-1.3 1-1 3.3.7 5.2 1.6 1.6 3.9 2.3 5.2 1 1.3-1 1-3.3-.7-5.2-1.6-1.6-3.9-2.3-5.2-1zm-10.8-8.1c-.7 1.3.3 2.9 2.3 3.9 1.6 1 3.6.7 4.3-.7.7-1.3-.3-2.9-2.3-3.9-2-.6-3.6-.3-4.3.7zm32.4 35.6c-1.6 1.3-1 4.3 1.3 6.2 2.3 2.3 5.2 2.6 6.5 1 1.3-1.3.7-4.3-1.3-6.2-2.2-2.3-5.2-2.6-6.5-1zm-11.4-14.7c-1.6 1-1.6 3.6 0 5.9 1.6 2.3 4.3 3.3 5.6 2.3 1.6-1.3 1.6-3.9 0-6.2-1.4-2.3-4-3.3-5.6-2z"></path>
                          </svg>
                      </a>
                  </td>
              </tr>
          <?php endforeach; ?>
          </tbody>
      </table>
      <p>After three failing builds, the system gives up until the commit hash changes.</p>
  <?php endif; ?>
</div>
</body>
</html>